"""Frequency Parsing Module for NIDAN AI Phase 5.

Normalizes standard frequency expressions (OD, BD, TID, QID, Q8H, PRN, etc.)
into standardized codes (OD, BID, TID, QID, PRN) and human-readable text.
Prioritizes explicit primary daily frequency codes over auxiliary timing phrases.
"""

import re
from typing import Optional, Tuple
from app.modules.prescription_intelligence.medication.vocabulary import FREQUENCY_MAP

# Primary frequency terms that define the daily administration frequency
PRIMARY_FREQUENCIES = [
    ("once daily", ("OD", "once daily")),
    ("once a day", ("OD", "once daily")),
    ("twice daily", ("BID", "twice daily")),
    ("twice a day", ("BID", "twice daily")),
    ("three times daily", ("TID", "three times daily")),
    ("thrice daily", ("TID", "three times daily")),
    ("four times daily", ("QID", "four times daily")),
    ("every 12 hours", ("Q12H", "every 12 hours")),
    ("every 8 hours", ("Q8H", "every 8 hours")),
    ("every 6 hours", ("Q6H", "every 6 hours")),
    ("od", ("OD", "once daily")),
    ("qd", ("OD", "once daily")),
    ("bd", ("BID", "twice daily")),
    ("bid", ("BID", "twice daily")),
    ("tds", ("TID", "three times daily")),
    ("tid", ("TID", "three times daily")),
    ("qid", ("QID", "four times daily")),
    ("q8h", ("Q8H", "every 8 hours")),
    ("q12h", ("Q12H", "every 12 hours")),
    ("q6h", ("Q6H", "every 6 hours")),
    ("weekly", ("QW", "once weekly")),
    ("once weekly", ("QW", "once weekly")),
    ("every other day", ("QOD", "every other day")),
]


class FrequencyParser:
    """Deterministic parser for medication frequency and PRN status."""

    @classmethod
    def parse_frequency(cls, text: str) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Parses frequency code, standard description, and PRN status from prescription line.
        Returns:
            (frequency_code, frequency_text, is_prn)
        """
        if not text:
            return None, None, False

        text_lower = text.lower()
        is_prn = bool(re.search(r"\b(?:prn|p\.r\.n\.|as\s+needed|sos|when\s+required)\b", text_lower))

        # 1. Check primary frequency terms first
        for phrase, (code, desc) in PRIMARY_FREQUENCIES:
            pattern = rf"\b{re.escape(phrase)}\b"
            if re.search(pattern, text_lower):
                return code, desc, is_prn

        # 2. Check full map (including secondary timing like 'at bedtime', 'qhs', 'qam')
        for freq_phrase, (code, desc) in sorted(FREQUENCY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            pattern = rf"\b{re.escape(freq_phrase)}\b"
            if re.search(pattern, text_lower):
                return code, desc, is_prn

        # 3. Numeric frequency patterns like "1-0-1" (BD), "1-1-1" (TID), "1-0-0" (OD), "0-0-1" (OD at night)
        sig_pattern = r"\b([012])\s*[-–]\s*([012])\s*[-–]\s*([012])(?:\s*[-–]\s*([012]))?\b"
        sig_match = re.search(sig_pattern, text_lower)
        if sig_match:
            doses = [int(g) for g in sig_match.groups() if g is not None]
            total_daily = sum(doses)
            if len(doses) == 3:
                if total_daily == 1:
                    return "OD", "once daily", is_prn
                elif total_daily == 2:
                    return "BID", "twice daily", is_prn
                elif total_daily == 3:
                    return "TID", "three times daily", is_prn
            elif len(doses) == 4 and total_daily == 4:
                return "QID", "four times daily", is_prn

        if is_prn:
            return "PRN", "as needed", True

        return None, None, False
