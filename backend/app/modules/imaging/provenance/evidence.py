from typing import Any, Dict, Optional
from app.modules.imaging.models import ImagingFinding, ImagingStudy, ImagingAnalysis


def build_imaging_evidence_item(
    finding: ImagingFinding,
    study: Optional[ImagingStudy] = None,
    analysis: Optional[ImagingAnalysis] = None,
):
    """
    Constructs an evidence item with verifiable provenance for Doctor Copilot and audit drilldown.
    """
    from app.modules.doctor_copilot.schemas import EvidenceItem, EvidenceType

    evidence_id = f"EVID-XRAY-{finding.id[:8].upper()}"
    study_date = study.study_date.isoformat() if study and study.study_date else None
    
    details: Dict[str, Any] = {
        "finding_code": finding.finding_code,
        "anatomical_region": finding.anatomical_region,
        "probability": finding.probability,
        "model_threshold": finding.model_threshold,
        "confidence": finding.confidence,
        "severity": finding.severity,
        "review_status": finding.review_status,
        "clinician_comment": finding.clinician_comment,
        "localization": finding.localization_json,
        "evidence_json": finding.evidence_json,
    }

    if study:
        details["study_id"] = study.id
        details["modality"] = study.modality
        details["body_part"] = study.body_part
        details["view_position"] = study.view_position
        details["image_quality_status"] = study.image_quality_status

    if analysis:
        details["analysis_id"] = analysis.id
        details["model_id"] = analysis.model_id
        details["model_version"] = analysis.model_version
        details["preprocessing_version"] = analysis.preprocessing_version
        details["threshold_version"] = analysis.threshold_version
        details["input_hash"] = analysis.input_hash

    return EvidenceItem(
        evidence_id=evidence_id,
        type=getattr(EvidenceType, "IMAGING_FINDING", EvidenceType.CLINICAL_FINDING),
        patient_id=study.patient_id if study else "",
        document_id=study.medical_document_id if study else None,
        finding_id=finding.id,
        date=study_date,
        source_text=finding.explanation or f"Radiographic pattern analysis for {finding.finding_name}.",
        value=f"{finding.probability * 100:.1f}% model probability (Threshold: {finding.model_threshold * 100:.1f}%)",
        status=finding.review_status,
        severity=finding.severity,
        confidence=finding.confidence,
        review_status=finding.review_status,
        title=f"Chest X-Ray Finding: {finding.finding_name}",
        details=details,
    )
