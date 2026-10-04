from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.modules.clinical_intelligence.models import (
    ClinicalObservation,
    SummarySectionTypeEnum,
)
from app.modules.clinical_intelligence.longitudinal.trend_engine import AnalyteTrendResult
from app.modules.clinical_intelligence.longitudinal.dynamics_engine import AbnormalityDynamicItem
from app.modules.clinical_intelligence.longitudinal.panel_completeness import PanelCompletenessResult
from app.modules.clinical_intelligence.engine.safety_validator import SafetyValidator


class GeneratedSummarySection(BaseModel):
    section_type: str
    title: str
    generated_text: str
    evidence_ids: List[str] = Field(default_factory=list)
    source_documents: List[str] = Field(default_factory=list)
    source_entities: List[str] = Field(default_factory=list)
    generated_by: str = "DETERMINISTIC_ENGINE"
    generation_version: str = "1.0.0"
    safety_validation_status: str = "PASSED"


class LongitudinalSummaryEngine:
    """Deterministic, structured, and fully traceable multi-visit clinical summary synthesizer."""

    @classmethod
    def generate_summary(
        cls,
        patient_id: str,
        observations: List[ClinicalObservation],
        trends: List[AnalyteTrendResult],
        dynamics: Any,
        panel_results: List[PanelCompletenessResult],
    ) -> List[GeneratedSummarySection]:
        sections: List[GeneratedSummarySection] = []

        # If dynamics is a report object, extract items
        dynamics_items: List[AbnormalityDynamicItem] = []
        if hasattr(dynamics, "items"):
            dynamics_items = dynamics.items
        elif isinstance(dynamics, list):
            dynamics_items = dynamics

        if not observations:

            sections.append(
                GeneratedSummarySection(
                    section_type=SummarySectionTypeEnum.OVERVIEW.value,
                    title="Longitudinal Clinical Summary Overview",
                    generated_text="No laboratory observations are currently available for this patient.",
                )
            )
            return sections

        sorted_obs = sorted(observations, key=lambda o: o.observation_date or datetime.min)
        first_date = sorted_obs[0].observation_date.strftime("%B %Y") if sorted_obs[0].observation_date else "Unknown Date"
        last_date = sorted_obs[-1].observation_date.strftime("%B %Y") if sorted_obs[-1].observation_date else "Unknown Date"
        doc_ids = list(dict.fromkeys([o.document_id for o in sorted_obs]))
        obs_ids = [o.id for o in sorted_obs]
        ent_ids = [o.entity_id for o in sorted_obs if o.entity_id]

        # -------------------------------------------------------------
        # Section 1: Overview
        # -------------------------------------------------------------
        overview_lines = [
            f"Observation period: {first_date} – {last_date}.",
            f"Total laboratory reports analyzed: {len(doc_ids)}.",
            f"Total structured analyte observations evaluated: {len(observations)}.",
            "Longitudinal analysis tracks chronological variations across laboratory encounters; clinical correlation recommended.",
        ]
        sections.append(
            cls._create_validated_section(
                section_type=SummarySectionTypeEnum.OVERVIEW.value,
                title="Longitudinal Clinical Summary Overview",
                text=" ".join(overview_lines),
                evidence_ids=obs_ids,
                source_documents=doc_ids,
                source_entities=ent_ids,
            )
        )

        # -------------------------------------------------------------
        # Section 2: Key Laboratory Trends
        # -------------------------------------------------------------
        trend_lines = []
        trend_ev_ids = []
        for t in trends:
            if t.observation_count >= 2 and t.direction != "INSUFFICIENT_DATA":
                trend_lines.append(f"• {t.explanation}")
                trend_ev_ids.extend([pt.get("observation_id") for pt in t.history_points if pt.get("observation_id")])

        if trend_lines:
            sections.append(
                cls._create_validated_section(
                    section_type=SummarySectionTypeEnum.LABORATORY_TRENDS.value,
                    title="Key Laboratory Trends",
                    text="\n".join(trend_lines),
                    evidence_ids=trend_ev_ids,
                    source_documents=doc_ids,
                    source_entities=ent_ids,
                )
            )

        # -------------------------------------------------------------
        # Section 3: Persistent Abnormalities
        # -------------------------------------------------------------
        persistent = [d for d in dynamics_items if d.classification == "PERSISTENT_ABNORMALITY"]
        if persistent:
            p_lines = [f"• {p.title}: {p.explanation}" for p in persistent]
            p_ev = [ev for p in persistent for ev in p.evidence_observation_ids]
            sections.append(
                cls._create_validated_section(
                    section_type=SummarySectionTypeEnum.PERSISTENT_ABNORMALITIES.value,
                    title="Persistent Laboratory Abnormalities",
                    text="\n".join(p_lines),
                    evidence_ids=p_ev,
                    source_documents=doc_ids,
                    source_entities=ent_ids,
                )
            )

        # -------------------------------------------------------------
        # Section 4: New Findings
        # -------------------------------------------------------------
        new_findings = [d for d in dynamics_items if d.classification == "NEW_ABNORMALITY" and d.persistence_count == 1]
        if new_findings:
            n_lines = [f"• {n.title}: {n.explanation}" for n in new_findings]
            n_ev = [ev for n in new_findings for ev in n.evidence_observation_ids]
            sections.append(
                cls._create_validated_section(
                    section_type=SummarySectionTypeEnum.NEW_FINDINGS.value,
                    title="New Laboratory Findings",
                    text="\n".join(n_lines),
                    evidence_ids=n_ev,
                    source_documents=doc_ids,
                    source_entities=ent_ids,
                )
            )

        # -------------------------------------------------------------
        # Section 5: Resolved Findings
        # -------------------------------------------------------------
        resolved = [d for d in dynamics_items if d.classification == "RESOLVED_ABNORMALITY"]
        if resolved:
            r_lines = [f"• {r.title}: {r.explanation}" for r in resolved]
            r_ev = [ev for r in resolved for ev in r.evidence_observation_ids]
            sections.append(
                cls._create_validated_section(
                    section_type=SummarySectionTypeEnum.RESOLVED_FINDINGS.value,
                    title="Resolved Laboratory Findings",
                    text="\n".join(r_lines),
                    evidence_ids=r_ev,
                    source_documents=doc_ids,
                    source_entities=ent_ids,
                )
            )

        # -------------------------------------------------------------
        # Section 6: Recurring Findings
        # -------------------------------------------------------------
        recurring = [d for d in dynamics_items if d.classification == "RECURRING_ABNORMALITY"]
        if recurring:
            rec_lines = [f"• {rc.title}: {rc.explanation}" for rc in recurring]
            rec_ev = [ev for rc in recurring for ev in rc.evidence_observation_ids]
            sections.append(
                cls._create_validated_section(
                    section_type=SummarySectionTypeEnum.RECURRING_FINDINGS.value,
                    title="Recurring Laboratory Findings",
                    text="\n".join(rec_lines),
                    evidence_ids=rec_ev,
                    source_documents=doc_ids,
                    source_entities=ent_ids,
                )
            )

        # -------------------------------------------------------------
        # Section 7: Data Quality & Panel Completeness
        # -------------------------------------------------------------
        quality_lines = []
        # Missing date checks
        missing_date_cnt = len([o for o in observations if o.observation_date_source in ("UPLOAD_TIMESTAMP", "UNKNOWN")])
        if missing_date_cnt > 0:
            quality_lines.append(f"• {missing_date_cnt} observation(s) used fallback timestamps due to missing explicit collection/report dates.")

        # Partial panel advisories
        for p in panel_results:
            if not p.is_complete:
                quality_lines.append(f"• {p.advisory_message}")

        if quality_lines:
            sections.append(
                cls._create_validated_section(
                    section_type=SummarySectionTypeEnum.DATA_QUALITY.value,
                    title="Data Quality & Panel Completeness Advisories",
                    text="\n".join(quality_lines),
                    evidence_ids=obs_ids,
                    source_documents=doc_ids,
                    source_entities=ent_ids,
                )
            )

        return sections

    @classmethod
    def generate_summary_sections(
        cls,
        patient_id: str,
        observations: List[ClinicalObservation],
        trends: List[AnalyteTrendResult],
        dynamics: Any,
        panel_results: List[PanelCompletenessResult],
    ) -> List[GeneratedSummarySection]:
        return cls.generate_summary(
            patient_id=patient_id,
            observations=observations,
            trends=trends,
            dynamics=dynamics,
            panel_results=panel_results,
        )

    @classmethod
    def _create_validated_section(
        cls,
        section_type: str,
        title: str,
        text: str,
        evidence_ids: List[str],
        source_documents: List[str],
        source_entities: List[str],
    ) -> GeneratedSummarySection:
        res = SafetyValidator.validate_text(text)
        status = "PASSED" if res.is_safe else "SANITIZED"
        final_text = text if res.is_safe else "Longitudinal summary text was adjusted to maintain non-diagnostic CDSS compliance."

        return GeneratedSummarySection(
            section_type=section_type,
            title=title,
            generated_text=final_text,
            evidence_ids=evidence_ids,
            source_documents=source_documents,
            source_entities=source_entities,
            generated_by="DETERMINISTIC_ENGINE",
            generation_version="1.0.0",
            safety_validation_status=status,
        )
