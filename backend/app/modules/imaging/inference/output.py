import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from app.modules.imaging.models import FindingStatusThresholdEnum
from app.modules.imaging.inference.xray_label_registry import XRAY_LABEL_TAXONOMY, get_xray_label


@dataclass
class CalibrationMetadata:
    calibration_method: str = "TEMPERATURE_SCALING"  # TEMPERATURE_SCALING, PLATT_SCALING, NOT_CALIBRATED
    calibration_dataset: str = "NIH_CHESTXRAY_14_VAL_CALIB"
    calibration_version: str = "1.0"
    calibration_date: str = "2026-09-01"
    temperature: float = 1.15
    is_calibrated: bool = True


@dataclass
class NormalizedFindingOutput:
    finding_code: str
    finding_name: str
    anatomical_region: str
    raw_probability: float
    calibrated_probability: float
    confidence: float
    model_threshold: float
    status: str  # BELOW_MODEL_THRESHOLD, ABOVE_MODEL_THRESHOLD, UNCERTAIN, MODEL_ERROR
    uncertainty_note: Optional[str] = None
    localization_boxes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ModelInferenceResult:
    model_id: str
    model_version: str
    preprocessing_version: str
    inference_version: str
    threshold_version: str
    calibration_metadata: CalibrationMetadata
    findings: List[NormalizedFindingOutput]
    raw_predictions: Dict[str, float]
    inference_time_ms: int
    is_demo_mock: bool = False
    model_readiness_status: str = "DEMO_TEST_ONLY"
    model_type: str = "TEST_HARNESS"


class ModelOutputNormalizer:
    """
    Transforms raw model logits/probabilities into calibrated, thresholded,
    and uncertainty-aware structured outputs.
    """

    UNCERTAINTY_MARGIN = 0.06  # Probabilities within ±0.06 of threshold flagged as UNCERTAIN

    @classmethod
    def apply_temperature_calibration(cls, raw_prob: float, temp: float = 1.15) -> float:
        """Applies temperature scaling calibration on probability."""
        if raw_prob <= 0.0:
            return 0.001
        if raw_prob >= 1.0:
            return 0.999
        # Convert to logit, scale by temperature, then sigmoid
        logit = math.log(raw_prob / (1.0 - raw_prob))
        calibrated_logit = logit / max(temp, 0.1)
        calibrated_prob = 1.0 / (1.0 + math.exp(-calibrated_logit))
        return round(min(max(calibrated_prob, 0.001), 0.999), 4)

    @classmethod
    def normalize(
        cls,
        raw_predictions: Dict[str, float],
        custom_thresholds: Optional[Dict[str, float]] = None,
        calibration: Optional[CalibrationMetadata] = None,
    ) -> List[NormalizedFindingOutput]:
        calib = calibration or CalibrationMetadata()
        custom_thresholds = custom_thresholds or {}
        normalized_list: List[NormalizedFindingOutput] = []

        for code, raw_val in raw_predictions.items():
            label_def = get_xray_label(code)
            finding_name = label_def.display_name if label_def else code.replace("_", " ").title()
            region = label_def.anatomical_region if label_def else "LUNG"
            threshold = custom_thresholds.get(code, label_def.default_threshold if label_def else 0.50)

            # 1. Bounds sanity
            clamped_raw = min(max(float(raw_val), 0.0), 1.0)

            # 2. Calibration
            if calib.is_calibrated and calib.calibration_method != "NOT_CALIBRATED":
                calibrated_prob = cls.apply_temperature_calibration(clamped_raw, calib.temperature)
            else:
                calibrated_prob = clamped_raw

            # 3. Confidence estimation (higher distance from threshold = higher confidence)
            dist = abs(calibrated_prob - threshold)
            confidence = round(min(1.0, 0.5 + (dist * 1.0)), 3)

            # 4. Uncertainty & Status Decision
            if abs(calibrated_prob - threshold) <= cls.UNCERTAINTY_MARGIN:
                status = FindingStatusThresholdEnum.UNCERTAIN.value
                uncertainty_note = f"Probability ({calibrated_prob*100:.1f}%) is within borderline decision boundary ({threshold*100:.1f}% ± 6%). Clinician verification required."
            elif calibrated_prob >= threshold:
                status = FindingStatusThresholdEnum.ABOVE_MODEL_THRESHOLD.value
                uncertainty_note = None
            else:
                status = FindingStatusThresholdEnum.BELOW_MODEL_THRESHOLD.value
                uncertainty_note = None

            # Bounding box / localization heuristic based on anatomical region
            loc_boxes: List[Dict[str, Any]] = []
            if status in (FindingStatusThresholdEnum.ABOVE_MODEL_THRESHOLD.value, FindingStatusThresholdEnum.UNCERTAIN.value):
                # Provide standard bounding region
                if "MEDIASTINUM" in region:
                    loc_boxes.append({"x": 0.35, "y": 0.45, "width": 0.30, "height": 0.35, "label": finding_name})
                elif "PLEURAL" in region:
                    loc_boxes.append({"x": 0.65, "y": 0.65, "width": 0.25, "height": 0.25, "label": finding_name})
                else:
                    loc_boxes.append({"x": 0.20, "y": 0.30, "width": 0.60, "height": 0.45, "label": finding_name})

            normalized_list.append(
                NormalizedFindingOutput(
                    finding_code=code,
                    finding_name=finding_name,
                    anatomical_region=region,
                    raw_probability=round(clamped_raw, 4),
                    calibrated_probability=round(calibrated_prob, 4),
                    confidence=confidence,
                    model_threshold=round(threshold, 4),
                    status=status,
                    uncertainty_note=uncertainty_note,
                    localization_boxes=loc_boxes,
                )
            )

        # Sort findings descending by calibrated probability
        normalized_list.sort(key=lambda x: x.calibrated_probability, reverse=True)
        return normalized_list
