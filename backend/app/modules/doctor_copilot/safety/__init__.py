"""
Safety & Guardrail Package for NIDAN AI Doctor Copilot.
Enforces CDSS Level 1 & 2 boundaries, hallucination checks, and unsupported claim detection.
"""
from app.modules.doctor_copilot.safety.prohibited_requests import is_prohibited_request, build_prohibited_refusal
from app.modules.doctor_copilot.safety.hallucination_guard import HallucinationGuard
from app.modules.doctor_copilot.safety.unsupported_claim_detector import UnsupportedClaimDetector
from app.modules.doctor_copilot.safety.safety_validator import CopilotSafetyValidator

__all__ = [
    "is_prohibited_request",
    "build_prohibited_refusal",
    "HallucinationGuard",
    "UnsupportedClaimDetector",
    "CopilotSafetyValidator",
]
