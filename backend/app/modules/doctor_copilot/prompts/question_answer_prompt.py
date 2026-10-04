import json
from typing import Any, Dict, List
from app.modules.doctor_copilot.schemas import EvidenceItem


def build_question_answer_prompt(
    query: str,
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

    return f"""CLINICIAN QUESTION:
"{query}"

AVAILABLE VERIFIED EVIDENCE ITEMS:
{json.dumps(ev_json, indent=2)}

DATA QUALITY NOTES:
{json.dumps(patient_context.get("data_quality_notes", []), indent=2)}

INSTRUCTIONS:
1. Answer the clinician's question using ONLY the provided evidence items.
2. For any patient-specific statement, attach the supporting evidence IDs in the claims array.
3. If information is not in the evidence, state that it is unavailable.
4. If general medical knowledge was asked, clearly separate general clinical concepts from patient-specific data.
"""
