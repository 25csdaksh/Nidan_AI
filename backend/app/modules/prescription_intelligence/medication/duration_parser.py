"""Duration Parsing Module for NIDAN AI Phase 5.

Extracts explicit durations (e.g. '5 days', '2 weeks', '1 month', '30 days').
Strict Rule: NEVER infer duration from quantity (e.g. '10 tablets' is NOT '10 days').
"""

import re
from typing import Optional, Tuple


class DurationParser:
    """Deterministic parser for explicit prescription duration."""

    @classmethod
    def parse_duration(cls, text: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Extracts duration value (e.g. 5, 14, 30) and unit ('DAYS', 'WEEKS', 'MONTHS', 'YEARS').
        """
        if not text:
            return None, None

        text_lower = text.lower()

        # Match 'for X days/weeks/months' or 'X days/weeks/months' or 'x 5 days' or 'x 7d'
        pattern = r"\b(?:for\s+|x\s*)?(\d+)\s*(days?|d|weeks?|wks?|w|months?|mos?|m|years?|yrs?|y)\b"
        match = re.search(pattern, text_lower)
        if match:
            try:
                val = int(match.group(1))
                unit_str = match.group(2).lower()

                if unit_str in {"days", "day", "d"}:
                    return val, "DAYS"
                elif unit_str in {"weeks", "week", "wks", "wk", "w"}:
                    return val, "WEEKS"
                elif unit_str in {"months", "month", "mos", "mo", "m"}:
                    return val, "MONTHS"
                elif unit_str in {"years", "year", "yrs", "yr", "y"}:
                    return val, "YEARS"
            except (ValueError, IndexError):
                pass

        return None, None
