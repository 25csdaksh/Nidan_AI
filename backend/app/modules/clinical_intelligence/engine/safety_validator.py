import re
from typing import List, Tuple
from pydantic import BaseModel


class SafetyValidationResult(BaseModel):
    is_safe: bool
    violations: List[str]
    sanitized_text: str


class SafetyValidator:
    """Safety guardrail validator asserting CDSS Level 1 & 2 compliance.

    Strictly forbids:
    - Definitive diagnoses
    - Disease prognosis or future outcome prediction
    - Medication recommendations / prescriptions
    - Dosage instructions
    - Autonomous treatment claims
    - Unsupported causal inferences
    """

    PROHIBITED_PATTERNS = [
        # Diagnosis claims
        r"\b(?:diagnosis\s*:|diagnosed\s+with|has\s+been\s+diagnosed\s+with|is\s+diagnosed\s+with)\b",
        r"\byou\s+have\s+(?:diabetes|anemia|ckd|cancer|disease|infection|hypothyroidism|hyperthyroidism)\b",
        r"\bpatient\s+has\s+(?:diabetes|anemia|ckd|cancer|disease|infection|hypothyroidism|hyperthyroidism)\b",
        
        # Prescription & Medication instructions
        r"\b(?:prescribe|prescription\s*:|prescribed\s*:|prescribe\s+[a-zA-Z]+)\b",
        r"\b(?:you\s+should\s+take|patient\s+should\s+take|take\s+this\s+medicine|take\s+iron|take\s+metformin|take\s+insulin|start\s+taking)\b",
        r"\b(?:start\s+medication|start\s+treatment|dosage\s*:\s*\d+|administer\s+\d+)\b",
        r"\b(?:recommended\s+dose|recommended\s+dosage)\b",
        r"\b(?:you\s+need\s+this\s+medicine|you\s+need\s+treatment)\b",
        
        # Treatment effectiveness / Patient outcome judgments
        r"\b(?:patient\s+is\s+getting\s+worse|patient\s+is\s+cured|treatment\s+is\s+working)\b",
        r"\b(?:patient\s+will\s+develop|will\s+develop\s+diabetes|will\s+develop\s+ckd|prognosis\s*:|will\s+develop\s+[a-zA-Z]+)\b",
        
        # Unsupported causal inferences
        r"\b(?:caused\s+by\s+the\s+change\s+in|caused\s+egfr\s+to|caused\s+creatinine\s+to|caused\s+[a-zA-Z]+\s+to)\b",
        r"\b(?:increased\s+creatinine\s+caused|decreased\s+hemoglobin\s+caused)\b",
    ]

    @classmethod
    def validate_text(cls, text: str) -> SafetyValidationResult:
        if not text:
            return SafetyValidationResult(is_safe=True, violations=[], sanitized_text="")

        violations = []
        for pattern in cls.PROHIBITED_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                violations.append(f"Prohibited autonomous clinical phrase detected: '{match.group(0)}'")

        is_safe = len(violations) == 0
        return SafetyValidationResult(
            is_safe=is_safe,
            violations=violations,
            sanitized_text=text,
        )

    @classmethod
    def validate_finding(
        cls,
        title: str,
        explanation: str,
        clinical_association: str = None,
    ) -> Tuple[bool, List[str]]:
        """Validate all human-readable fields of a clinical finding."""
        violations = []

        t_res = cls.validate_text(title)
        if not t_res.is_safe:
            violations.extend([f"Title: {v}" for v in t_res.violations])

        e_res = cls.validate_text(explanation)
        if not e_res.is_safe:
            violations.extend([f"Explanation: {v}" for v in e_res.violations])

        if clinical_association:
            c_res = cls.validate_text(clinical_association)
            if not c_res.is_safe:
                violations.extend([f"Clinical Association: {v}" for v in c_res.violations])

        return (len(violations) == 0, violations)
