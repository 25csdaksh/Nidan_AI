from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.modules.clinical_intelligence.models import (
    ClinicalObservation,
    AbnormalityDynamicsEnum,
)


class AbnormalityDynamicItem(BaseModel):
    analyte: str
    canonical_name: str
    classification: str  # PERSISTENT_ABNORMALITY, NEW_ABNORMALITY, RESOLVED_ABNORMALITY, RECURRING_ABNORMALITY, FLUCTUATING, NORMAL, STABLE
    title: str
    explanation: str
    persistence_count: int = 0
    first_observed: Optional[datetime] = None
    last_observed: Optional[datetime] = None
    evidence_observation_ids: List[str] = Field(default_factory=list)
    evidence_documents: List[str] = Field(default_factory=list)
    recent_statuses: List[str] = Field(default_factory=list)


class LongitudinalDynamicsReport(BaseModel):
    items: List[AbnormalityDynamicItem] = Field(default_factory=list)
    persistent_abnormalities: List[AbnormalityDynamicItem] = Field(default_factory=list)
    new_abnormalities: List[AbnormalityDynamicItem] = Field(default_factory=list)
    resolved_abnormalities: List[AbnormalityDynamicItem] = Field(default_factory=list)
    recurring_abnormalities: List[AbnormalityDynamicItem] = Field(default_factory=list)
    fluctuations: List[AbnormalityDynamicItem] = Field(default_factory=list)
    data_quality_warnings: List[str] = Field(default_factory=list)
    summary_counts: Dict[str, int] = Field(default_factory=dict)


class AbnormalityDynamicsEngine:
    """Deterministic classifier for longitudinal abnormality state transitions."""

    @classmethod
    def evaluate_single_analyte(
        cls,
        canonical_name: str,
        observations: List[ClinicalObservation],
    ) -> AbnormalityDynamicItem:
        if not observations:
            return AbnormalityDynamicItem(
                analyte=canonical_name,
                canonical_name=canonical_name,
                classification=AbnormalityDynamicsEnum.INSUFFICIENT_DATA.value,
                title=f"{canonical_name} - Insufficient Longitudinal Data",
                explanation="No observations available for dynamic classification.",
            )

        sorted_obs = sorted(
            observations,
            key=lambda o: o.observation_date or datetime.min,
        )

        analyte_display = sorted_obs[-1].analyte or canonical_name
        statuses = [o.technical_status for o in sorted_obs]
        obs_ids = [o.id for o in sorted_obs]
        doc_ids = list(dict.fromkeys([o.document_id for o in sorted_obs]))
        first_date = sorted_obs[0].observation_date
        last_date = sorted_obs[-1].observation_date

        if len(sorted_obs) == 1:
            curr_status = statuses[0]
            if curr_status in ("LOW", "HIGH", "CRITICAL_LOW", "CRITICAL_HIGH"):
                return AbnormalityDynamicItem(
                    analyte=analyte_display,
                    canonical_name=canonical_name,
                    classification=AbnormalityDynamicsEnum.PERSISTENT_ABNORMALITY.value,
                    title=f"Single Abnormal Observation for {analyte_display}",
                    explanation=f"Single observed value for {analyte_display} is {curr_status.lower()}; additional encounters are required to assess longitudinal persistence.",
                    persistence_count=1,
                    first_observed=first_date,
                    last_observed=last_date,
                    evidence_observation_ids=obs_ids,
                    evidence_documents=doc_ids,
                    recent_statuses=statuses,
                )
            return AbnormalityDynamicItem(
                analyte=analyte_display,
                canonical_name=canonical_name,
                classification=AbnormalityDynamicsEnum.NORMAL.value,
                title=f"{analyte_display} Within Reported Interval",
                explanation=f"{analyte_display} was within reported reference intervals on the single available encounter.",
                persistence_count=0,
                first_observed=first_date,
                last_observed=last_date,
                evidence_observation_ids=obs_ids,
                evidence_documents=doc_ids,
                recent_statuses=statuses,
            )

        prev_status = statuses[-2]
        curr_status = statuses[-1]

        # -------------------------------------------------------------
        # 1. Fluctuation Detection (HIGH -> LOW -> HIGH or LOW -> HIGH -> LOW)
        # -------------------------------------------------------------
        if len(statuses) >= 3:
            s_window = [s for s in statuses[-3:]]
            if (s_window[0] in ("HIGH", "CRITICAL_HIGH") and s_window[1] in ("LOW", "CRITICAL_LOW") and s_window[2] in ("HIGH", "CRITICAL_HIGH")) or \
               (s_window[0] in ("LOW", "CRITICAL_LOW") and s_window[1] in ("HIGH", "CRITICAL_HIGH") and s_window[2] in ("LOW", "CRITICAL_LOW")):
                return AbnormalityDynamicItem(
                    analyte=analyte_display,
                    canonical_name=canonical_name,
                    classification=AbnormalityDynamicsEnum.FLUCTUATING.value,
                    title=f"Fluctuating Values Observed in {analyte_display}",
                    explanation=f"Laboratory value shows bidirectional fluctuation across available longitudinal observations ({' -> '.join(statuses[-3:])}). Clinical correlation recommended.",
                    persistence_count=0,
                    first_observed=first_date,
                    last_observed=last_date,
                    evidence_observation_ids=obs_ids[-3:],
                    evidence_documents=doc_ids,
                    recent_statuses=statuses,
                )

        # -------------------------------------------------------------
        # 2. Recurring Abnormality (LOW -> NORMAL -> LOW or HIGH -> NORMAL -> HIGH)
        # -------------------------------------------------------------
        if len(statuses) >= 3:
            s_window = statuses[-3:]
            if (s_window[0] in ("LOW", "CRITICAL_LOW") and s_window[1] == "NORMAL" and s_window[2] in ("LOW", "CRITICAL_LOW")) or \
               (s_window[0] in ("HIGH", "CRITICAL_HIGH") and s_window[1] == "NORMAL" and s_window[2] in ("HIGH", "CRITICAL_HIGH")):
                status_desc = "low" if s_window[2] in ("LOW", "CRITICAL_LOW") else "elevated"
                return AbnormalityDynamicItem(
                    analyte=analyte_display,
                    canonical_name=canonical_name,
                    classification=AbnormalityDynamicsEnum.RECURRING_ABNORMALITY.value,
                    title=f"Recurring {status_desc.capitalize()} {analyte_display} Finding",
                    explanation=f"Recurring abnormal laboratory pattern observed across multiple reports ({' -> '.join(statuses[-3:])}).",
                    persistence_count=2,
                    first_observed=sorted_obs[-3].observation_date,
                    last_observed=last_date,
                    evidence_observation_ids=obs_ids[-3:],
                    evidence_documents=doc_ids,
                    recent_statuses=statuses,
                )

        # -------------------------------------------------------------
        # 3. Persistent Abnormality (LOW-LOW-LOW or HIGH-HIGH-HIGH)
        # -------------------------------------------------------------
        consecutive_cnt = 0
        target_group = None
        for s in reversed(statuses):
            is_low = s in ("LOW", "CRITICAL_LOW")
            is_high = s in ("HIGH", "CRITICAL_HIGH")

            if target_group is None:
                if is_low:
                    target_group = "LOW"
                    consecutive_cnt += 1
                elif is_high:
                    target_group = "HIGH"
                    consecutive_cnt += 1
                else:
                    break
            else:
                if (target_group == "LOW" and is_low) or (target_group == "HIGH" and is_high):
                    consecutive_cnt += 1
                else:
                    break

        if consecutive_cnt >= 2:
            status_desc = "low" if target_group == "LOW" else "elevated"
            return AbnormalityDynamicItem(
                analyte=analyte_display,
                canonical_name=canonical_name,
                classification=AbnormalityDynamicsEnum.PERSISTENT_ABNORMALITY.value,
                title=f"Persistent {status_desc.capitalize()} {analyte_display}",
                explanation=f"Persistent {status_desc} {analyte_display} values observed across {consecutive_cnt} consecutive report encounters.",
                persistence_count=consecutive_cnt,
                first_observed=sorted_obs[-consecutive_cnt].observation_date,
                last_observed=last_date,
                evidence_observation_ids=obs_ids[-consecutive_cnt:],
                evidence_documents=doc_ids,
                recent_statuses=statuses,
            )

        # -------------------------------------------------------------
        # 4. New Abnormality Transition (NORMAL -> ABNORMAL)
        # -------------------------------------------------------------
        if prev_status == "NORMAL" and curr_status in ("LOW", "HIGH", "CRITICAL_LOW", "CRITICAL_HIGH"):
            status_desc = "low" if curr_status in ("LOW", "CRITICAL_LOW") else "elevated"
            return AbnormalityDynamicItem(
                analyte=analyte_display,
                canonical_name=canonical_name,
                classification=AbnormalityDynamicsEnum.NEW_ABNORMALITY.value,
                title=f"New {status_desc.capitalize()} {analyte_display} Finding",
                explanation=f"New {status_desc} laboratory finding observed compared with the previous available report.",
                persistence_count=1,
                first_observed=sorted_obs[-1].observation_date,
                last_observed=last_date,
                evidence_observation_ids=obs_ids[-2:],
                evidence_documents=doc_ids,
                recent_statuses=statuses,
            )

        # -------------------------------------------------------------
        # 5. Resolved Abnormality Transition (ABNORMAL -> NORMAL)
        # -------------------------------------------------------------
        if prev_status in ("LOW", "HIGH", "CRITICAL_LOW", "CRITICAL_HIGH") and curr_status == "NORMAL":
            return AbnormalityDynamicItem(
                analyte=analyte_display,
                canonical_name=canonical_name,
                classification=AbnormalityDynamicsEnum.RESOLVED_ABNORMALITY.value,
                title=f"{analyte_display} Normalized to Reference Range",
                explanation=f"Previously abnormal value is within the current reported reference range.",
                persistence_count=0,
                first_observed=first_date,
                last_observed=last_date,
                evidence_observation_ids=obs_ids[-2:],
                evidence_documents=doc_ids,
                recent_statuses=statuses,
            )

        # -------------------------------------------------------------
        # 6. Stable Normal
        # -------------------------------------------------------------
        return AbnormalityDynamicItem(
            analyte=analyte_display,
            canonical_name=canonical_name,
            classification=AbnormalityDynamicsEnum.NORMAL.value,
            title=f"{analyte_display} Consistently Within Range",
            explanation=f"{analyte_display} values remained within reference intervals across available encounters.",
            persistence_count=0,
            first_observed=first_date,
            last_observed=last_date,
            evidence_observation_ids=obs_ids,
            evidence_documents=doc_ids,
            recent_statuses=statuses,
        )

    @classmethod
    def evaluate_dynamics(
        cls,
        observations: List[ClinicalObservation],
    ) -> LongitudinalDynamicsReport:
        """
        Evaluates dynamic transitions across all distinct analytes in the observation set.
        """
        grouped: Dict[str, List[ClinicalObservation]] = {}
        for obs in observations:
            key = obs.canonical_name or obs.analyte
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(obs)

        all_items: List[AbnormalityDynamicItem] = []
        persistent: List[AbnormalityDynamicItem] = []
        new_items: List[AbnormalityDynamicItem] = []
        resolved: List[AbnormalityDynamicItem] = []
        recurring: List[AbnormalityDynamicItem] = []
        fluctuations: List[AbnormalityDynamicItem] = []

        for cname, obs_list in grouped.items():
            item = cls.evaluate_single_analyte(cname, obs_list)
            all_items.append(item)
            if item.classification == AbnormalityDynamicsEnum.PERSISTENT_ABNORMALITY.value:
                persistent.append(item)
            elif item.classification == AbnormalityDynamicsEnum.NEW_ABNORMALITY.value:
                new_items.append(item)
            elif item.classification == AbnormalityDynamicsEnum.RESOLVED_ABNORMALITY.value:
                resolved.append(item)
            elif item.classification == AbnormalityDynamicsEnum.RECURRING_ABNORMALITY.value:
                recurring.append(item)
            elif item.classification == AbnormalityDynamicsEnum.FLUCTUATING.value:
                fluctuations.append(item)

        return LongitudinalDynamicsReport(
            items=all_items,
            persistent_abnormalities=persistent,
            new_abnormalities=new_items,
            resolved_abnormalities=resolved,
            recurring_abnormalities=recurring,
            fluctuations=fluctuations,
            summary_counts={
                "persistent_count": len(persistent),
                "new_count": len(new_items),
                "resolved_count": len(resolved),
                "recurring_count": len(recurring),
                "fluctuation_count": len(fluctuations),
            },
        )
