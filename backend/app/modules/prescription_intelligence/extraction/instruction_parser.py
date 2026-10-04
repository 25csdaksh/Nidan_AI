"""Instruction Parsing Module for NIDAN AI Phase 5.

Extracts timing instructions, meal relationships (before meals, after meals),
and administration instructions from prescription text lines.
"""

import re
from typing import Optional
from app.modules.prescription_intelligence.medication.vocabulary import MEAL_INSTRUCTIONS_MAP


class InstructionParser:
    """Parses patient administration instructions and meal timings."""

    @classmethod
    def parse_instructions(cls, text: str) -> Optional[str]:
        if not text:
            return None

        text_lower = text.lower()
        instructions = []

        # Check meal timings
        for meal_kw, meal_desc in MEAL_INSTRUCTIONS_MAP.items():
            pattern = rf"\b{re.escape(meal_kw)}\b"
            if re.search(pattern, text_lower):
                if meal_desc not in instructions:
                    instructions.append(meal_desc)

        # Other instructions
        if "with water" in text_lower or "plenty of water" in text_lower:
            instructions.append("with plenty of water")
        if "bedtime" in text_lower or "at night" in text_lower or "hs" in text_lower:
            if "at bedtime" not in instructions:
                instructions.append("at bedtime")
        if "morning" in text_lower or "in the morning" in text_lower:
            if "in the morning" not in instructions:
                instructions.append("in the morning")

        if instructions:
            return ", ".join(instructions)

        return None
