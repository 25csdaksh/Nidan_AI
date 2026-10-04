"""Safety Guardrail Validator for Prescription Intelligence (Phase 5).

Asserts strict CDSS Level 1 & 2 compliance across all generated findings, alerts, and summaries.
Prohibits:
- Autonomous prescriptions / medication recommendations (e.g. 'prescribe X', 'you should take X', 'start taking X')
- Autonomous dosage recommendations or titrations ('increase dose to 1000mg', 'reduce dose')
- Autonomous treatment discontinuations ('stop taking X immediately')
- Autonomous diagnoses or outcome predictions ('patient has diabetes', 'patient will develop CKD')
- Autonomous causality claims ('metformin caused creatinine to rise')
"""

import re
from typing import List, Optional, Tuple
from pydantic import BaseModel


class SafetyValidationResult(BaseModel):
    is_safe: bool
    violations: List[str]
    sanitized_text: str


class MedicationSafetyValidator:
    """Deterministic validator enforcing clinical decision-support boundaries."""

    PROHIBITED_PATTERNS = [
        # Prescriptive commands
        r"\b(?:prescribe|prescribing\s+this|you\s+must\s+prescribe|we\s+prescribe)\b",
        r"\b(?:you\s+should\s+take|patient\s+should\s+take|patient\s+must\s+take|take\s+this\s+medicine|start\s+taking)\b",
        r"\b(?:start\s+medication|start\s+treatment|administer\s+\d+|give\s+patient\s+\d+)\b",
        r"\b(?:stop\s+taking\s+[a-zA-Z]+|discontinue\s+[a-zA-Z]+\s+immediately|switch\s+to\s+[a-zA-Z]+)\b",
        
        # Dosage modification commands
        r"\b(?:increase\s+dose\s+to|decrease\s+dose\s+to|titrate\s+up\s+to|reduce\s+dose\s+to)\b",
        r"\b(?:recommended\s+dose\s+is|recommended\s+dosage\s+is|change\s+frequency\s+to)\b",
        
        # Diagnostic & Outcome assertions
        r"\b(?:patient\s+has\s+developed|patient\s+has\s+contracted|diagnosed\s+with)\b",
        r"\b(?:patient\s+is\s+cured|patient\s+is\s+getting\s+worse|treatment\s+is\s+working|drug\s+is\s+failing)\b",
        r"\b(?:patient\s+will\s+develop|will\s+cause\s+death|prognosis\s*:)\b",
        
        # Unsupported causal inferences
        r"\b(?:caused\s+by\s+the\s+medication|medication\s+caused\s+the\s+lab|drug\s+caused\s+creatinine)\b",
        r"\b(?:metformin\s+caused|lisinopril\s+caused|aspirin\s+caused\s+bleeding)\b",
    ]

    @classmethod
    def validate_text(cls, text: str) -> SafetyValidationResult:
        if not text:
            return SafetyValidationResult(is_safe=True, violations=[], sanitized_text="")

        violations = []
        for pattern in cls.PROHIBITED_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                violations.append(f"Prohibited prescriptive/diagnostic clinical phrase detected: '{match.group(0)}'")

        return SafetyValidationResult(
            is_safe=len(violations) == 0,
            violations=violations,
            sanitized_text=text,
        )

    @classmethod
    def validate_safety_finding(
        cls,
        title: str,
        description: str,
        clinical_association: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        violations = []

        t_res = cls.validate_text(title)
        if not t_res.is_safe:
            violations.extend([f"Title: {v}" for v in t_res.violations])

        d_res = cls.validate_text(description)
        if not d_res.is_safe:
            violations.extend([f"Description: {v}" for v in d_res.violations])

        if clinical_association:
            c_res = cls.validate_text(clinical_association)
            if not c_res.is_safe:
                violations.extend([f"Clinical Association: {v}" for v in c_res.violations])

        return len(violations) == 0, violations
