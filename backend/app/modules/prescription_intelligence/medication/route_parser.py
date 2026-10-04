"""Route of Administration Parsing Module for NIDAN AI Phase 5.

Extracts explicit routes (oral, IV, IM, SC, topical, etc.).
Strict Rule: NEVER infers route from dosage form alone unless explicitly present in the text.
"""

import re
from typing import Optional
from app.modules.prescription_intelligence.medication.vocabulary import ROUTES_MAP


class RouteParser:
    """Deterministic parser for explicit administration routes."""

    @classmethod
    def parse_route(cls, text: str) -> Optional[str]:
        if not text:
            return None

        text_lower = text.lower()

        # Check multi-word routes first (e.g. 'by mouth', 'eye drops')
        for route_phrase, canonical_route in sorted(ROUTES_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            pattern = rf"\b{re.escape(route_phrase)}\b"
            if re.search(pattern, text_lower):
                return canonical_route

        return None
