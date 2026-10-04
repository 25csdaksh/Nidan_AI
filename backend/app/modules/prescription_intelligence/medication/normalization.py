"""Controlled Medication Normalization for NIDAN AI.

Applies deterministic dictionary lookups and controlled alias resolution.
Strict non-fuzzy policy: Insufficiently matched drugs resolve to 'UNKNOWN'
to mandate human clinician review rather than risking harmful misidentifications.
"""

import re
from typing import Optional, Tuple
from app.modules.prescription_intelligence.medication.vocabulary import (
    DOSAGE_FORMS,
    MEDICATION_CATALOG,
)


class MedicationNormalizer:
    """Normalizes raw medication strings into canonical and generic names."""

    @classmethod
    def clean_medication_name(cls, raw_text: str) -> str:
        """Strips noise, prefixes (Rx, Tab, Cap), and strength suffixes."""
        if not raw_text:
            return ""

        text = raw_text.strip()
        # Remove leading Rx, bullet points, numbers
        text = re.sub(r"^(?:rx[\s:\.\-]*|\d+[\.\)\-]\s*|[\*\-\•]\s*)", "", text, flags=re.IGNORECASE)

        # Remove leading dosage form keywords (Tab, Cap, Inj, Syrup, etc.)
        for form in sorted(DOSAGE_FORMS, key=len, reverse=True):
            pattern = rf"^{re.escape(form)}\.?\s+"
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove trailing strength like '500mg', '500 mg', '10 mg', '0.5mg'
        text = re.sub(r"\s+\d+(?:\.\d+)?\s*(?:mg|g|mcg|ug|ml|iu|u|%|meq)\b.*$", "", text, flags=re.IGNORECASE)

        # Clean punctuation
        text = text.strip(" ,.-:;")
        return text

    @classmethod
    def normalize(cls, raw_text: str) -> Tuple[str, Optional[str], Optional[str], float]:
        """
        Normalizes a raw medication name.
        Returns:
            (canonical_name, generic_name, brand_name, confidence)
        """
        if not raw_text or not raw_text.strip():
            return "UNKNOWN", None, None, 0.0

        cleaned = cls.clean_medication_name(raw_text).strip()
        if not cleaned:
            return "UNKNOWN", None, None, 0.0

        cleaned_lower = cleaned.lower()

        # Direct / Alias lookup in catalog
        for canonical, data in MEDICATION_CATALOG.items():
            if cleaned_lower == canonical.lower():
                return canonical, data.get("generic"), None, 1.0

            # Check aliases
            if cleaned_lower in data.get("aliases", set()):
                # Determine if cleaned_lower matches a brand name
                matched_brand = None
                for b in data.get("brand_names", set()):
                    if cleaned_lower == b.lower():
                        matched_brand = b
                        break
                return canonical, data.get("generic"), matched_brand, 0.95

        # Multi-word alias check (e.g. "Metformin HCl" -> "Metformin")
        for canonical, data in MEDICATION_CATALOG.items():
            for alias in data.get("aliases", set()):
                if alias in cleaned_lower:
                    # Ensure word boundary match
                    pattern = rf"\b{re.escape(alias)}\b"
                    if re.search(pattern, cleaned_lower):
                        matched_brand = None
                        for b in data.get("brand_names", set()):
                            if b.lower() in cleaned_lower:
                                matched_brand = b
                                break
                        return canonical, data.get("generic"), matched_brand, 0.90

        # Non-matched fallback (strict non-hallucination policy)
        return "UNKNOWN", None, None, 0.40
