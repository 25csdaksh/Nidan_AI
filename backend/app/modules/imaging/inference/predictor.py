import hashlib
import time
from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.modules.imaging.inference.base import BaseImagingModel, ModelMetadata
from app.modules.imaging.inference.output import (
    CalibrationMetadata,
    ModelInferenceResult,
    ModelOutputNormalizer,
    NormalizedFindingOutput,
)
from app.modules.imaging.inference.xray_label_registry import XRAY_LABEL_TAXONOMY


class ChestXRayDeterministicTestModel(BaseImagingModel):
    """
    Deterministic Test Harness Model for software verification and automated testing.
    Explicitly labeled: DEMO / TEST ONLY.
    Never claims autonomous clinical accuracy.
    Derives deterministic, reproducible probability scores from image content hashes.
    """

    MODEL_ID = "XRAY_CHEST_FOUNDATION_V1"
    VERSION = "1.0.0"
    FRAMEWORK = "DETERMINISTIC_TEST_HARNESS"
    PREPROCESSING_VERSION = "xray-preprocess-v1"
    THRESHOLD_VERSION = "xray-thresh-v1"

    def __init__(self):
        self._is_loaded = False

    def load(self) -> bool:
        self._is_loaded = True
        return True

    def predict(
        self,
        image_bytes: bytes,
        preprocessed_matrix: List[List[float]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Generates deterministic pseudo-probabilities strictly based on input byte digest.
        Guarantees exact reproducibility across test runs.
        """
        h = hashlib.sha256(image_bytes).hexdigest()
        predictions: Dict[str, float] = {}

        # Use bytes of the hash to seed deterministic values
        labels = list(XRAY_LABEL_TAXONOMY.keys())
        for idx, label in enumerate(labels):
            # Take a 4-char slice of hash
            hex_chunk = h[(idx * 2) % 60 : (idx * 2) % 60 + 4]
            int_val = int(hex_chunk, 16)
            # Map into [0.05, 0.95] range
            base_prob = 0.05 + (int_val % 900) / 1000.0

            # If the image is very dark or uniform, lower probabilities
            if preprocessed_matrix:
                flat_vals = [p for row in preprocessed_matrix for p in row]
                mean_val = sum(flat_vals) / max(len(flat_vals), 1)
                if mean_val < 0.1:
                    base_prob *= 0.5

            predictions[label] = round(base_prob, 4)

        return predictions

    def validate_output(self, raw_predictions: Dict[str, float]) -> Dict[str, float]:
        validated = {}
        for code, val in raw_predictions.items():
            if code in XRAY_LABEL_TAXONOMY:
                validated[code] = min(max(float(val), 0.0), 1.0)
        return validated

    def metadata(self) -> ModelMetadata:
        return ModelMetadata(
            model_id=self.MODEL_ID,
            version=self.VERSION,
            modality="XRAY",
            framework=self.FRAMEWORK,
            input_size=[512, 512],
            supported_views=["PA", "AP", "Lateral"],
            labels=list(XRAY_LABEL_TAXONOMY.keys()),
            training_dataset_reference="NIDAN_AI_TEST_SUITE_SYNTHETIC_DATASET_V1",
            intended_use="ASSISTIVE_TEST_HARNESS_AND_INTEGRATION_VERIFICATION",
            limitations=[
                "Software test harness only - NOT validated for clinical diagnosis.",
                "Requires mandatory clinician review for every observation.",
                "Does not replace certified radiologists or physicians.",
            ],
            threshold_version=self.THRESHOLD_VERSION,
            calibration_status="CALIBRATED",
            calibration_version="1.0",
            is_production_ready=False,
            model_sha256="01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b",
            model_type="TEST_HARNESS",
            readiness_status="DEMO_TEST_ONLY",
            weights_status="NOT_APPLICABLE",
        )


class ImagingPredictor:
    """
    Inference coordinator executing image prediction, timing, output normalization,
    and calibration.
    """

    def __init__(self, model: Optional[Any] = None):
        if isinstance(model, str):
            from app.modules.imaging.inference.model_registry import get_model_registry

            resolved = get_model_registry().get_model(model)
            self.model = resolved or ChestXRayDeterministicTestModel()
        elif isinstance(model, BaseImagingModel):
            self.model = model
        else:
            self.model = ChestXRayDeterministicTestModel()

        self.model.load()

    def run_inference(
        self,
        image_bytes: bytes,
        preprocessed_matrix: List[List[float]],
        context: Optional[Dict[str, Any]] = None,
    ) -> ModelInferenceResult:
        start_time = time.perf_counter()

        raw_preds = self.model.predict(image_bytes, preprocessed_matrix, context)
        validated_preds = self.model.validate_output(raw_preds)

        calib = CalibrationMetadata()
        normalized_findings = ModelOutputNormalizer.normalize(
            validated_preds,
            custom_thresholds=context.get("custom_thresholds") if context else None,
            calibration=calib,
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        meta = self.model.metadata()

        return ModelInferenceResult(
            model_id=meta.model_id,
            model_version=meta.version,
            preprocessing_version="xray-preprocess-v1",
            inference_version="1.0.0",
            threshold_version=meta.threshold_version,
            calibration_metadata=calib,
            findings=normalized_findings,
            raw_predictions=validated_preds,
            inference_time_ms=elapsed_ms,
            is_demo_mock=not meta.is_production_ready,
            model_readiness_status=meta.readiness_status,
            model_type=meta.model_type,
        )
