from typing import Any, Dict, List
from app.modules.imaging.models import FindingReviewStatusEnum, ImagingFinding
from app.modules.imaging.inference.output import NormalizedFindingOutput
from app.modules.imaging.findings.safety import ImagingSafetyValidator


class FindingBuilder:
    """
    Constructs ImagingFinding database models from normalized inference outputs.
    Ensures safe clinical phrasing and structures evidence provenance metadata.
    """

    @classmethod
    def build_finding(
        cls,
        analysis_id: str,
        norm_output: NormalizedFindingOutput,
        model_version: str,
    ) -> ImagingFinding:
        explanation = ImagingSafetyValidator.sanitize_or_wrap_finding_explanation(
            norm_output.finding_name,
            norm_output.calibrated_probability,
            norm_output.model_threshold,
            norm_output.anatomical_region,
        )

        severity = "HIGH" if norm_output.calibrated_probability >= 0.75 else (
            "MODERATE" if norm_output.calibrated_probability >= norm_output.model_threshold else "INFO"
        )

        evidence_payload = {
            "model_version": model_version,
            "raw_probability": norm_output.raw_probability,
            "calibrated_probability": norm_output.calibrated_probability,
            "model_threshold": norm_output.model_threshold,
            "confidence": norm_output.confidence,
            "status": norm_output.status,
            "uncertainty_note": norm_output.uncertainty_note,
        }

        localization_payload = {
            "boxes": norm_output.localization_boxes,
            "disclaimer": "Model attention/localization visualization. Not confirmed anatomical boundary.",
        }

        return ImagingFinding(
            imaging_analysis_id=analysis_id,
            finding_code=norm_output.finding_code,
            finding_name=norm_output.finding_name,
            anatomical_region=norm_output.anatomical_region,
            probability=norm_output.calibrated_probability,
            confidence=norm_output.confidence,
            severity=severity,
            model_threshold=norm_output.model_threshold,
            localization_json=localization_payload,
            explanation=explanation,
            evidence_json=evidence_payload,
            review_status=FindingReviewStatusEnum.PENDING.value,
        )


def build_findings_from_inference(
    analysis_id: str,
    normalized_findings: List[NormalizedFindingOutput],
    model_version: str,
) -> List[ImagingFinding]:
    return [
        FindingBuilder.build_finding(analysis_id, f, model_version)
        for f in normalized_findings
    ]
