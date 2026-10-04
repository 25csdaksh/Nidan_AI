"""
Evaluation & Benchmarking harness for Doctor Copilot.
"""
from typing import Any, Dict, List
from app.modules.doctor_copilot.schemas import StructuredCopilotResponse, SafetyStatus, SupportLevel


class CopilotEvaluator:
    """
    Evaluates generated Copilot responses against deterministic quality and safety benchmarks.
    """

    def evaluate_response(self, response: StructuredCopilotResponse) -> Dict[str, Any]:
        total_claims = len(response.claims)
        supported_claims = sum(1 for c in response.claims if c.support_level == SupportLevel.SUPPORTED)
        unsupported_claims = sum(1 for c in response.claims if c.support_level == SupportLevel.UNSUPPORTED)

        citation_rate = (supported_claims / total_claims) if total_claims > 0 else 1.0

        return {
            "safety_passed": response.safety_status in [SafetyStatus.PASSED, SafetyStatus.PROHIBITED_REQUEST],
            "requires_clinician_review": response.requires_clinician_review,
            "total_claims": total_claims,
            "supported_claims": supported_claims,
            "unsupported_claims": unsupported_claims,
            "citation_rate": citation_rate,
            "evidence_count": len(response.evidence_items),
            "records_considered": response.records_considered,
        }
