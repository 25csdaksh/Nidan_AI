from typing import Optional, List
from app.modules.clinical_intelligence.reference_ranges.schemas import ResolvedReferenceRange
from app.modules.clinical_intelligence.reference_ranges.catalog import (
    REFERENCE_RANGE_CATALOG,
    ReferenceRangeDefinition,
)
from app.modules.medical_documents.models import DocumentExtractionEntity
from app.modules.medical_documents.extraction.normalizer import normalize_unit


class ReferenceRangeResolver:
    """Demographic-aware, priority-governed Reference Range Resolver."""

    def __init__(self, custom_catalog: Optional[List[ReferenceRangeDefinition]] = None):
        self.catalog = custom_catalog if custom_catalog is not None else REFERENCE_RANGE_CATALOG

    def resolve(
        self,
        entity: DocumentExtractionEntity,
        patient_sex: Optional[str] = None,
        patient_age: Optional[float] = None,
        pregnancy_status: Optional[str] = None,
    ) -> ResolvedReferenceRange:
        canonical_name = entity.canonical_name or getattr(entity, "raw_name", "")
        analyte_display = getattr(entity, "raw_name", None) or entity.canonical_name or ""
        normalized_unit, _ = normalize_unit(entity.normalized_unit or entity.original_unit)

        # -------------------------------------------------------------
        # 1. Doctor-reviewed / Laboratory-provided Range
        # -------------------------------------------------------------
        if entity.review_status == "ACCEPTED" and (entity.reference_min is not None or entity.reference_max is not None):
            return ResolvedReferenceRange(
                analyte=analyte_display,
                canonical_name=canonical_name,
                source_type="DOCTOR_REVIEWED",
                source_name="Clinician Review / Laboratory Validated",
                source_version="1.0",
                resolution_reason="Clinician-accepted laboratory reported reference interval.",
                unit=normalized_unit,
                lower_bound=entity.reference_min,
                upper_bound=entity.reference_max,
                is_resolved=True,
                raw_reference_text=entity.reference_range_text,
            )

        # -------------------------------------------------------------
        # 2. Report-provided Reference Range
        # -------------------------------------------------------------
        if entity.reference_min is not None or entity.reference_max is not None:
            return ResolvedReferenceRange(
                analyte=analyte_display,
                canonical_name=canonical_name,
                source_type="REPORT",
                source_name="Extracted Laboratory Report",
                source_version="Report Raw",
                resolution_reason="Extracted directly from laboratory report document text.",
                unit=normalized_unit,
                lower_bound=entity.reference_min,
                upper_bound=entity.reference_max,
                is_resolved=True,
                raw_reference_text=entity.reference_range_text,
            )

        # -------------------------------------------------------------
        # 3. Applicable Configured Knowledge Base Range
        # -------------------------------------------------------------
        matches = self._find_matching_definitions(
            canonical_name=canonical_name,
            unit=normalized_unit,
            sex=patient_sex,
            age=patient_age,
            pregnancy_status=pregnancy_status,
        )

        if matches:
            best_match = matches[0]
            reason = f"Resolved from clinical knowledge base ({best_match.source_name} v{best_match.source_version}) for demographics (Sex: {best_match.sex}, Age: {best_match.age_min}-{best_match.age_max}y)."
            return ResolvedReferenceRange(
                analyte=analyte_display,
                canonical_name=canonical_name,
                source_type="KNOWLEDGE_BASE",
                source_name=best_match.source_name,
                source_version=best_match.source_version,
                resolution_reason=reason,
                unit=best_match.unit,
                lower_bound=best_match.lower_bound,
                upper_bound=best_match.upper_bound,
                critical_low=best_match.critical_low,
                critical_high=best_match.critical_high,
                is_resolved=True,
                raw_reference_text=None,
            )

        # -------------------------------------------------------------
        # 4. Unresolved Demographic / Knowledge Base Gap
        # -------------------------------------------------------------
        reason_parts = []
        if not patient_sex and not patient_age:
            reason_parts.append("patient sex and age unavailable")
        elif not patient_sex:
            reason_parts.append("patient sex unavailable")
        elif patient_age is None:
            reason_parts.append("patient age unavailable")

        if not normalized_unit:
            reason_parts.append("analyte unit unresolved")

        unresolved_reason = (
            f"Applicable reference range could not be determined from available demographic information ({', '.join(reason_parts)})."
            if reason_parts
            else "No verified reference range definition available for this analyte and unit configuration."
        )

        return ResolvedReferenceRange(
            analyte=analyte_display,
            canonical_name=canonical_name,
            source_type="UNKNOWN",
            source_name=None,
            source_version=None,
            resolution_reason=unresolved_reason,
            unit=normalized_unit,
            lower_bound=None,
            upper_bound=None,
            is_resolved=False,
            raw_reference_text=entity.reference_range_text,
        )

    def _find_matching_definitions(
        self,
        canonical_name: str,
        unit: Optional[str],
        sex: Optional[str],
        age: Optional[float],
        pregnancy_status: Optional[str],
    ) -> List[ReferenceRangeDefinition]:
        candidates: List[ReferenceRangeDefinition] = []
        normalized_cname = canonical_name.lower().strip()

        for defn in self.catalog:
            if defn.canonical_name.lower().strip() != normalized_cname:
                continue

            # Unit check if unit is specified
            if unit and defn.unit.lower().strip() != unit.lower().strip():
                continue

            # Pregnancy check
            if pregnancy_status and pregnancy_status.lower() != "all":
                if defn.pregnancy_status != "all" and defn.pregnancy_status.lower() != pregnancy_status.lower():
                    continue

            # Sex check
            if sex:
                clean_sex = sex.lower().strip()
                if defn.sex != "all" and defn.sex.lower() != clean_sex:
                    continue

            # Age check
            if age is not None:
                if not (defn.age_min <= age <= defn.age_max):
                    continue

            candidates.append(defn)

        # Sort candidates by specificity: exact sex match > "all", narrowest age range
        def specificity_score(d: ReferenceRangeDefinition) -> int:
            score = 0
            if sex and d.sex.lower() == sex.lower():
                score += 10
            if age is not None:
                range_span = d.age_max - d.age_min
                score += max(0, int(100 - range_span))
            if pregnancy_status and d.pregnancy_status.lower() == pregnancy_status.lower():
                score += 20
            return score

        candidates.sort(key=specificity_score, reverse=True)
        return candidates
