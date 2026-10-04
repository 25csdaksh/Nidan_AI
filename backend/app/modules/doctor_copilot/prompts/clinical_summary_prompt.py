import json
from typing import Any, Dict, List
from app.modules.doctor_copilot.schemas import EvidenceItem


def build_clinical_summary_prompt(
    patient_context: Dict[str, Any],
    evidence_items: List[EvidenceItem],
) -> str:
    ev_json = [
        {
            "evidence_id": item.evidence_id,
            "type": item.type.value if hasattr(item.type, "value") else str(item.type),
            "title": item.title,
            "value": item.value,
            "unit": item.unit,
            "status": item.status,
            "severity": item.severity,
            "date": item.date,
            "details": item.details,
        }
        for item in evidence_items
    ]

    patient_summary = {
        "patient_id": patient_context.get("patient", {}).get("patient_id"),
        "mrn": patient_context.get("patient", {}).get("mrn"),
        "dob": patient_context.get("patient", {}).get("date_of_birth"),
        "gender": patient_context.get("patient", {}).get("gender"),
        "allergies": patient_context.get("patient", {}).get("allergies", []),
        "documents_count": patient_context.get("documents", {}).get("documents_count", 0),
        "data_quality_notes": patient_context.get("data_quality_notes", []),
    }

    return f"""TASK: Generate a comprehensive structured clinical consultation summary for the attending clinician.

PATIENT OVERVIEW:
{json.dumps(patient_summary, indent=2)}

AVAILABLE VERIFIED EVIDENCE ITEMS:
{json.dumps(ev_json, indent=2)}

INSTRUCTIONS:
1. Summarize key laboratory findings, persistent abnormalities, longitudinal trajectories, documented medications, and medication safety signals.
2. Explicitly cite all evidence IDs in your claims list.
3. List data limitations and missing records in the limitations list.
4. Maintain strict CDSS Level 1/2 boundaries.
"""
