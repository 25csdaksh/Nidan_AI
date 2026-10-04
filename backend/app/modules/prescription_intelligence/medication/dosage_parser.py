"""Dosage and Strength Parsing Module for NIDAN AI Phase 5.

Extracts:
- Numerical strength value and standard unit (e.g. 500 mg, 10 mcg)
- Dosage form (Tablet, Capsule, Syrup, etc.)
- Explicit dose quantity (e.g. 1 tablet, 2 puffs, 5 ml)
"""

import re
from typing import Optional, Tuple
from app.modules.prescription_intelligence.medication.vocabulary import (
    DOSAGE_FORM_CANONICAL,
    DOSAGE_FORMS,
    STRENGTH_UNITS,
)


class DosageParser:
    """Deterministic parser for drug strength, dosage form, and quantity."""

    @classmethod
    def parse_strength(cls, text: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Extracts strength numeric value and unit from text.
        e.g. 'Metformin 500 mg', 'Thyronorm 50mcg', '0.5 mg'
        """
        if not text:
            return None, None

        # Regex for number + unit: e.g. 500 mg, 500mg, 0.5 mcg, 10%
        pattern = r"\b(\d+(?:\.\d+)?)\s*(mg|g|mcg|ug|ml|iu|u|%|meq(?:/l)?|mg/ml|mg/5ml)\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                unit = match.group(2).lower()
                # Normalize unit variations
                if unit == "ug":
                    unit = "mcg"
                elif unit == "u":
                    unit = "IU"
                return val, unit
            except (ValueError, IndexError):
                pass

        return None, None

    @classmethod
    def parse_dosage_form(cls, text: str) -> Optional[str]:
        """
        Identifies explicit dosage form from text (e.g. Tab, Cap, Syrup, Injection).
        """
        if not text:
            return None

        words = re.findall(r"\b[a-zA-Z]+\.?\b", text.lower())
        for word in words:
            clean_word = word.rstrip(".")
            if clean_word in DOSAGE_FORM_CANONICAL:
                return DOSAGE_FORM_CANONICAL[clean_word]
            if word in DOSAGE_FORM_CANONICAL:
                return DOSAGE_FORM_CANONICAL[word]

        return None

    @classmethod
    def parse_dose_quantity(cls, text: str) -> Optional[str]:
        """
        Extracts explicit dose quantity, e.g.:
        '1 tablet', '2 caps', '1 puff', '5 ml', '1/2 tab'
        """
        if not text:
            return None

        pattern = r"\b(\d+(?:/\d+|\.\d+)?)\s*(tab(?:let)?s?|cap(?:sule)?s?|puff(?:s)?|drop(?:s)?|ml|tsp|tbsp|sachet(?:s)?)\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"{match.group(1)} {match.group(2).lower()}"

        return None
