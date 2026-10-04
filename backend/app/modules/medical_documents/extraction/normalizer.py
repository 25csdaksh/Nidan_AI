"""Unit normalization, numeric parsing, reference range parsing, and technical status evaluation.

Strictly non-diagnostic: comparisons are technical checks against reported ranges only.
"""

import re
from typing import Optional, Tuple
from pydantic import BaseModel


class NormalizedRange(BaseModel):
    raw_text: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None


# Unit standardization map
UNIT_MAP = {
    # Concentration mass
    "g/dl": "g/dL",
    "g/l": "g/L",
    "gm/dl": "g/dL",
    "g%": "g/dL",
    "mg/dl": "mg/dL",
    "mg%": "mg/dL",
    "mg/l": "mg/L",
    "ug/dl": "ug/dL",
    "µg/dl": "ug/dL",
    "mcg/dl": "ug/dL",
    "ug/l": "ug/L",
    "µg/l": "ug/L",
    "ng/ml": "ng/mL",
    "ng/dl": "ng/dL",
    "pg/ml": "pg/mL",
    "pg/dl": "pg/dL",
    # Concentration molar
    "mmol/l": "mmol/L",
    "umol/l": "umol/L",
    "µmol/l": "umol/L",
    "nmol/l": "nmol/L",
    "pmol/l": "pmol/L",
    "meq/l": "mEq/L",
    # Cellular counts
    "10^3/ul": "10^3/uL",
    "10^3/cumm": "10^3/uL",
    "thousand/ul": "10^3/uL",
    "thousand/cumm": "10^3/uL",
    "thous/cumm": "10^3/uL",
    "10^6/ul": "10^6/uL",
    "10^6/cumm": "10^6/uL",
    "million/ul": "10^6/uL",
    "million/cumm": "10^6/uL",
    "mil/ul": "10^6/uL",
    "cells/cumm": "/uL",
    "cells/cu.mm": "/uL",
    "cells/mcl": "/uL",
    "/cumm": "/uL",
    "/ul": "/uL",
    "/mm3": "/uL",
    "x10^9/l": "10^9/L",
    "x10^12/l": "10^12/L",
    # Enzymatic / Biological activity
    "u/l": "U/L",
    "iu/l": "IU/L",
    "uiu/ml": "uIU/mL",
    "µiu/ml": "uIU/mL",
    "miu/l": "mIU/L",
    "miu/ml": "mIU/mL",
    # Proportions & Indices
    "%": "%",
    "vol%": "%",
    "fl": "fL",
    "pg": "pg",
    "ml/min": "mL/min",
    "ml/min/1.73m2": "mL/min/1.73m2",
    "ml/min/1.73m^2": "mL/min/1.73m2",
}


def normalize_unit(raw_unit: Optional[str]) -> Tuple[Optional[str], bool]:
    """Normalize clinical unit string. Returns (normalized_unit, is_standardized)."""
    if not raw_unit:
        return None, False
    cleaned = raw_unit.lower().strip()
    # Direct dictionary lookup
    if cleaned in UNIT_MAP:
        return UNIT_MAP[cleaned], True

    # Check for prefix or trailing characters
    cleaned_stripped = cleaned.strip("()[],:;.")
    if cleaned_stripped in UNIT_MAP:
        return UNIT_MAP[cleaned_stripped], True

    return raw_unit.strip(), False


def parse_numeric_value(raw_val: str) -> Tuple[Optional[float], str]:
    """Extract numeric floating point value from string."""
    if not raw_val:
        return None, ""
    cleaned = raw_val.strip()
    # Match standard number pattern e.g. 9.2, 140, 0.05, < 0.01, > 60
    match = re.search(r"([<>]?\s*\d+(?:\.\d+)?)", cleaned)
    if not match:
        return None, cleaned

    matched_str = match.group(1).replace(" ", "")
    num_str = re.sub(r"[<>]", "", matched_str)
    try:
        val = float(num_str)
        return val, cleaned
    except ValueError:
        return None, cleaned


def parse_reference_range(raw_text: Optional[str]) -> Optional[NormalizedRange]:
    """Extract min, max, and unit from laboratory reference range text."""
    if not raw_text or not raw_text.strip():
        return None

    cleaned = raw_text.strip()
    # Pattern 1: Interval like '13.0 - 17.0', '13.0-17.0', '13.0 to 17.0', '4.5 - 5.5 g/dL'
    interval_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z/%^0-9\.\-]+)?", cleaned, re.IGNORECASE)
    if interval_match:
        try:
            min_val = float(interval_match.group(1))
            max_val = float(interval_match.group(2))
            unit_str = interval_match.group(3)
            norm_unit, _ = normalize_unit(unit_str) if unit_str else (None, False)
            return NormalizedRange(
                raw_text=cleaned,
                min_value=min_val,
                max_value=max_val,
                unit=norm_unit,
            )
        except ValueError:
            pass

    # Pattern 2: Upper bound only '< 200', '<= 200', 'Less than 200'
    less_match = re.search(r"(?:<|<=|less\s+than|up\s+to)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z/%^0-9\.\-]+)?", cleaned, re.IGNORECASE)
    if less_match:
        try:
            max_val = float(less_match.group(1))
            unit_str = less_match.group(2)
            norm_unit, _ = normalize_unit(unit_str) if unit_str else (None, False)
            return NormalizedRange(
                raw_text=cleaned,
                min_value=None,
                max_value=max_val,
                unit=norm_unit,
            )
        except ValueError:
            pass

    # Pattern 3: Lower bound only '> 60', '>= 60', 'Greater than 60'
    greater_match = re.search(r"(?:>|>=|greater\s+than|more\s+than)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z/%^0-9\.\-]+)?", cleaned, re.IGNORECASE)
    if greater_match:
        try:
            min_val = float(greater_match.group(1))
            unit_str = greater_match.group(2)
            norm_unit, _ = normalize_unit(unit_str) if unit_str else (None, False)
            return NormalizedRange(
                raw_text=cleaned,
                min_value=min_val,
                max_value=None,
                unit=norm_unit,
            )
        except ValueError:
            pass

    return NormalizedRange(raw_text=cleaned, min_value=None, max_value=None, unit=None)


def evaluate_technical_status(
    value: Optional[float],
    ref_min: Optional[float],
    ref_max: Optional[float],
) -> str:
    """Evaluate numeric value against reported reference range boundaries.

    Strictly technical comparison: returns 'BELOW_REPORTED_RANGE', 'WITHIN_REPORTED_RANGE',
    'ABOVE_REPORTED_RANGE', or 'UNKNOWN'.
    """
    if value is None:
        return "UNKNOWN"

    if ref_min is None and ref_max is None:
        return "UNKNOWN"

    if ref_min is not None and ref_max is not None:
        if value < ref_min:
            return "BELOW_REPORTED_RANGE"
        elif value > ref_max:
            return "ABOVE_REPORTED_RANGE"
        else:
            return "WITHIN_REPORTED_RANGE"

    if ref_min is not None:
        if value < ref_min:
            return "BELOW_REPORTED_RANGE"
        return "WITHIN_REPORTED_RANGE"

    if ref_max is not None:
        if value > ref_max:
            return "ABOVE_REPORTED_RANGE"
        return "WITHIN_REPORTED_RANGE"

    return "UNKNOWN"
