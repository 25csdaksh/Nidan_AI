"""Extraction confidence calculator.

Computes extraction_confidence (0.0 to 1.0) based on structural, OCR, and normalization factors.
Clearly labeled as extraction_confidence, NOT clinical certainty.
"""

from typing import Optional


class ConfidenceCalculator:
    """Calculates extraction confidence based on measurable heuristic signals."""

    @staticmethod
    def calculate(
        ocr_confidence: float = 1.0,
        is_exact_synonym_match: bool = True,
        has_numeric_value: bool = True,
        has_valid_unit: bool = True,
        has_reference_range: bool = False,
    ) -> float:
        # Base confidence weighted by OCR quality
        score = min(max(ocr_confidence, 0.0), 1.0) * 0.40

        # Terminology match confidence
        if is_exact_synonym_match:
            score += 0.30
        else:
            score += 0.15

        # Value parsing confidence
        if has_numeric_value:
            score += 0.15
        else:
            score += 0.05

        # Unit validity
        if has_valid_unit:
            score += 0.10
        else:
            score += 0.02

        # Bonus for structured reference range presence
        if has_reference_range:
            score += 0.05

        return round(min(score, 0.99), 2)
