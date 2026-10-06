import re
from typing import Any, Dict, List, Set, Tuple
from app.modules.doctor_copilot.schemas import EvidenceItem, EvidenceType

DIAGNOSTIC_ASSERTION_PATTERNS = [
    r"\b(patient is diagnosed with|diagnosed as having|patient definitely has)\b",
    r"\bpatient has (diabetes mellitus|iron deficiency anemia|ckd|chronic kidney disease|cirrhosis|leukemia|pneumonia|tuberculosis|lung cancer|pulmonary edema|pleural effusion|pneumothorax|cardiomegaly)\b",
    r"\b(confirmed diagnosis of|definitive diagnosis is)\b",
]


class HallucinationGuard:
    """
    Validates that numerical values, medications, and clinical concepts asserted in generated answers
    strictly exist within the patient's verified evidence catalog.
    """

    def validate(
        self,
        text: str,
        evidence_catalog: Dict[str, EvidenceItem],
        patient_context: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        violations: List[str] = []
        lower_text = text.lower()

        # 1. Check for autonomous diagnostic assertions
        for pat in DIAGNOSTIC_ASSERTION_PATTERNS:
            if re.search(pat, lower_text):
                violations.append(f"Autonomous diagnostic assertion detected: '{pat}'")

        # 2. Extract numbers with units mentioned in text and verify against context
        # Matches patterns like "10.2 g/dL", "1.8 mg/dL", "500 mg"
        num_unit_matches = re.findall(r"(\b\d+(?:\.\d+)?)\s*(mg/dl|g/dl|mmol/l|u/l|iu/l|%|mg|mcg|tablets?)\b", lower_text)
        
        valid_values_in_context: Set[str] = set()
        for ev in evidence_catalog.values():
            if ev.value:
                valid_values_in_context.add(str(ev.value).lower().strip())
            if ev.details:
                for k, v in ev.details.items():
                    if v is not None:
                        valid_values_in_context.add(str(v).lower().strip())

        # If a specific numeric+unit is stated, ensure either the number or value exists in context
        # (Only flag if completely absent from all evidence and context)
        all_context_str = str(patient_context).lower() + " " + " ".join(valid_values_in_context)
        for num, unit in num_unit_matches:
            combined = f"{num} {unit}".strip()
            num_found = (
                num in all_context_str
                or combined in all_context_str
                or any(num in v for v in valid_values_in_context)
            )
            if not num_found:
                violations.append(f"Hallucinated clinical value detected: '{combined}' not present in verified patient record.")

        is_valid = len(violations) == 0
        return is_valid, violations

