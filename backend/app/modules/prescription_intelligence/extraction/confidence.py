"""Extraction Confidence Scorer for Prescription Intelligence.

Computes deterministic, reproducible confidence scores for extracted medication entities.
Enforces review requirements when drug identity is unconfirmed or information is sparse.
"""

from typing import Optional


class PrescriptionConfidenceScorer:
    """Calculates extraction confidence for prescription medications."""

    @classmethod
    def calculate_confidence(
        cls,
        canonical_name: str,
        norm_confidence: float,
        strength_val: Optional[float],
        strength_unit: Optional[str],
        frequency_code: Optional[str],
        dosage_form: Optional[str],
        route: Optional[str],
        duration_val: Optional[int],
    ) -> float:
        """
        Calculates normalized confidence in range [0.0, 1.0].
        """
        if canonical_name == "UNKNOWN" or norm_confidence < 0.50:
            return round(min(0.45, norm_confidence), 2)

        score = norm_confidence * 0.60  # Base weight on drug identification

        # Component bonuses
        if strength_val is not None and strength_unit:
            score += 0.15
        elif strength_val is not None:
            score += 0.08

        if frequency_code:
            score += 0.10

        if dosage_form:
            score += 0.05

        if route:
            score += 0.05

        if duration_val is not None:
            score += 0.05

        return round(min(0.99, max(0.10, score)), 2)
