from typing import Any, Dict, Optional
from app.modules.doctor_copilot.schemas import EvidenceItem


def format_evidence_drilldown(item: EvidenceItem) -> Dict[str, Any]:
    """
    Constructs a clinician-facing drilldown structure for an evidence item.
    """
    return {
        "evidence_id": item.evidence_id,
        "type": item.type.value if hasattr(item.type, "value") else str(item.type),
        "title": item.title,
        "patient_id": item.patient_id,
        "document_id": item.document_id,
        "observation_id": item.observation_id,
        "finding_id": item.finding_id,
        "prescription_id": item.prescription_id,
        "medication_id": item.medication_id,
        "rule_id": item.rule_id,
        "date": item.date,
        "value": item.value,
        "unit": item.unit,
        "reference_range": item.reference_range,
        "status": item.status,
        "severity": item.severity,
        "confidence": item.confidence,
        "review_status": item.review_status,
        "source_text": item.source_text,
        "details": item.details,
    }
