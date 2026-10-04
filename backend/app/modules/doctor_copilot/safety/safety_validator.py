import re
from typing import Any, Dict, List, Tuple
from app.modules.doctor_copilot.schemas import (
    ClaimItem,
    EvidenceItem,
    SafetyStatus,
    StructuredCopilotResponse,
    SupportLevel,
)
from app.modules.doctor_copilot.safety.hallucination_guard import HallucinationGuard
from app.modules.doctor_copilot.safety.unsupported_claim_detector import UnsupportedClaimDetector

SAFETY_PROHIBITED_PATTERNS = [
    r"\b(prescribe|prescribing|i prescribe|prescribed to take)\b",
    r"\b(you should take|patient should take|administer|dosage is recommended at)\b",
    r"\b(confirmed diagnosis:|patient is definitively diagnosed with)\b",
    r"\b(will die within|survival prognosis is|curable with)\b",
    r"\b(increase the dose of|stop taking immediately)\b",
]


class CopilotSafetyValidator:
    """
    Master CDSS Safety Validator for generated Copilot responses.
    """

    def __init__(self):
        self.hallucination_guard = HallucinationGuard()
        self.claim_detector = UnsupportedClaimDetector()

    def validate_response(
        self,
        response: StructuredCopilotResponse,
        evidence_catalog: Dict[str, EvidenceItem],
        patient_context: Dict[str, Any],
    ) -> StructuredCopilotResponse:
        violations: List[str] = []
        lower_answer = response.answer.lower()

        # 1. Regex Prohibitions
        for pat in SAFETY_PROHIBITED_PATTERNS:
            if re.search(pat, lower_answer):
                violations.append(f"Prohibited phrasing matching pattern '{pat}'")

        # 2. Hallucination Check
        is_valid_hal, hal_violations = self.hallucination_guard.validate(
            response.answer, evidence_catalog, patient_context
        )
        violations.extend(hal_violations)

        # 3. Claims Validation
        validated_claims, claim_issues = self.claim_detector.validate_claims(
            response.claims, evidence_catalog
        )
        violations.extend(claim_issues)

        # If critical violations found, update status and append limitation notes
        if violations:
            # Check if critical enough to block or flag
            has_critical = any("Prohibited phrasing" in v or "Autonomous diagnostic" in v for v in violations)
            if has_critical:
                response.safety_status = SafetyStatus.BLOCKED
                response.answer = (
                    "Response blocked by NIDAN AI CDSS safety guardrails due to prescriptive or unsupported diagnostic phrasing. "
                    "Please review the verified laboratory observations, prescriptions, and clinical findings directly."
                )
                response.claims = []
            else:
                response.safety_status = SafetyStatus.FLAGGED
                response.claims = validated_claims

            for v in violations:
                response.limitations.append(f"Safety Note: {v}")
        else:
            response.safety_status = SafetyStatus.PASSED
            response.claims = validated_claims

        # Ensure mandatory clinician review is set
        response.requires_clinician_review = True
        return response
