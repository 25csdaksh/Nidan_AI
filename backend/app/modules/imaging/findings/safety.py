import re
from typing import List, Tuple

IMAGING_CDSS_DISCLAIMER = (
    "NIDAN AI Medical Imaging CDSS is an assistive tool for licensed healthcare professionals. "
    "Automated model outputs, probabilities, and localization maps are not confirmed diagnoses and "
    "do not replace clinical radiological interpretation. Human clinician review is mandatory."
)

PROHIBITED_IMAGING_PATTERNS = [
    r"\b(patient has (pneumonia|tuberculosis|cancer|covid|effusion|cardiomegaly|edema|fibrosis))\b",
    r"\b(patient definitely has|confirmed diagnosis of|definitive diagnosis is)\b",
    r"\b(start antibiotics?|administer medication|prescribe|increase dosage|stop medication)\b",
    r"\b(autonomous diagnosis|definitive radiologist report)\b",
]


class ImagingSafetyValidator:
    """
    Safety validator ensuring imaging findings, text, and CDSS responses comply
    with strict non-prescriptive, non-diagnostic clinical boundaries.
    """

    @classmethod
    def validate_text(cls, text: str) -> Tuple[bool, List[str]]:
        violations: List[str] = []
        lower = text.lower()

        for pat in PROHIBITED_IMAGING_PATTERNS:
            if re.search(pat, lower):
                violations.append(f"Prohibited autonomous diagnostic or prescriptive phrasing detected: '{pat}'")

        is_safe = len(violations) == 0
        return is_safe, violations

    @classmethod
    def sanitize_or_wrap_finding_explanation(
        cls,
        finding_name: str,
        calibrated_probability: float,
        threshold: float,
        anatomical_region: str,
    ) -> str:
        """
        Generates certified safe assistive finding explanation text.
        """
        prob_pct = f"{calibrated_probability * 100:.1f}%"
        thresh_pct = f"{threshold * 100:.1f}%"

        if calibrated_probability >= threshold:
            return (
                f"Automated vision model output shows an elevated probability of {prob_pct} (threshold: {thresh_pct}) "
                f"for a radiographic pattern associated with {finding_name} in the {anatomical_region}. "
                f"Finding requires radiologist/clinician verification. Automated model output is not a confirmed diagnosis."
            )
        else:
            return (
                f"Automated model output shows a probability of {prob_pct} (threshold: {thresh_pct}) "
                f"for {finding_name}, which is below the active decision threshold. Clinical review advised."
            )
