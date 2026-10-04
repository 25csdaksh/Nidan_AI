import json
from typing import Any, Dict, List
from app.modules.doctor_copilot.schemas import EvidenceItem


def build_comparison_prompt(
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

    return f"""CLINICIAN COMPARISON REQUEST:
"{query}"

AVAILABLE COMPARATIVE EVIDENCE & OBSERVATION TIMELINE:
{json.dumps(ev_json, indent=2)}

INSTRUCTIONS:
1. Contrast the values, statuses, and trajectories between historical and recent laboratory encounters.
2. Note persistent abnormalities, new findings, or resolved values.
3. Cite all evidence IDs accurately.
"""
