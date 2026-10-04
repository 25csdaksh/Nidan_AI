from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.modules.clinical_intelligence.models import (
    ClinicalObservation,
    TrendDirectionEnum,
    TrendStatusEnum,
)
from app.modules.clinical_intelligence.longitudinal.trend_rules import get_trend_rule, AnalyteTrendRule


class AnalyteTrendResult(BaseModel):
    analyte: str
    canonical_name: str
    unit: Optional[str] = None
    observation_count: int
    first_value: Optional[float] = None
    last_value: Optional[float] = None
    first_date: Optional[datetime] = None
    last_date: Optional[datetime] = None
    absolute_change: Optional[float] = None
    percentage_change: Optional[float] = None
    direction: str
    trend_status: str
    explanation: str
    history_points: List[Dict[str, Any]] = Field(default_factory=list)


class TrendEngine:
    """Deterministic, noise-aware clinical analyte trend engine."""

    @classmethod
    def evaluate_trends(cls, observations: List[ClinicalObservation]) -> List[AnalyteTrendResult]:
        """Evaluates longitudinal trends grouped by analyte across all observations."""
        grouped: Dict[str, List[ClinicalObservation]] = {}
        for obs in observations:
            key = obs.canonical_name or obs.analyte
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(obs)

        results = []
        for cname, obs_list in grouped.items():
            results.append(cls.evaluate_series(cname, obs_list))
        return results


    @classmethod
    def evaluate_series(
        cls,
        canonical_name: str,
        observations: List[ClinicalObservation],
    ) -> AnalyteTrendResult:
        if not observations:
            return AnalyteTrendResult(
                analyte=canonical_name,
                canonical_name=canonical_name,
                unit=None,
                observation_count=0,
                direction=TrendDirectionEnum.INSUFFICIENT_DATA.value,
                trend_status=TrendStatusEnum.INSUFFICIENT_DATA.value,
                explanation="No observations available for trend evaluation.",
            )

        # Sort observations chronologically
        sorted_obs = sorted(
            observations,
            key=lambda o: o.observation_date or datetime.min,
        )

        history_points = [
            {
                "observation_id": o.id,
                "document_id": o.document_id,
                "date": o.observation_date.strftime("%Y-%m-%d") if o.observation_date else None,
                "value": o.normalized_value if o.normalized_value is not None else o.value,
                "numeric_value": o.normalized_value,
                "unit": o.unit,
                "status": o.technical_status,
                "reference_min": o.reference_min,
                "reference_max": o.reference_max,
            }
            for o in sorted_obs
        ]

        valid_numeric_obs = [o for o in sorted_obs if o.normalized_value is not None]
        analyte_display = sorted_obs[-1].analyte or canonical_name
        unit = sorted_obs[-1].unit
        rule = get_trend_rule(canonical_name)

        if len(valid_numeric_obs) < 2:
            single_val = valid_numeric_obs[0].normalized_value if valid_numeric_obs else None
            single_date = valid_numeric_obs[0].observation_date if valid_numeric_obs else None
            return AnalyteTrendResult(
                analyte=analyte_display,
                canonical_name=canonical_name,
                unit=unit,
                observation_count=len(sorted_obs),
                first_value=single_val,
                last_value=single_val,
                first_date=single_date,
                last_date=single_date,
                direction=TrendDirectionEnum.INSUFFICIENT_DATA.value,
                trend_status=TrendStatusEnum.INSUFFICIENT_DATA.value,
                explanation="At least 2 longitudinal observations are required to compute a directional trend.",
                history_points=history_points,
            )

        first_obs = valid_numeric_obs[0]
        last_obs = valid_numeric_obs[-1]
        prev_obs = valid_numeric_obs[-2]

        first_val = first_obs.normalized_value
        last_val = last_obs.normalized_value
        prev_val = prev_obs.normalized_value

        abs_change = round(last_val - prev_val, 3)
        pct_change = None
        if prev_val is not None and prev_val != 0:
            pct_change = round(((last_val - prev_val) / abs(prev_val)) * 100.0, 2)

        # 1. Determine direction with noise/threshold filtering
        direction = TrendDirectionEnum.UNCHANGED.value
        is_neutral = False

        if abs(abs_change) <= rule.neutral_delta_abs:
            is_neutral = True
        elif pct_change is not None and abs(pct_change) < rule.neutral_delta_pct:
            is_neutral = True

        if is_neutral:
            direction = TrendDirectionEnum.UNCHANGED.value
        elif last_val > prev_val:
            direction = TrendDirectionEnum.INCREASED.value
        else:
            direction = TrendDirectionEnum.DECREASED.value

        # 2. Determine clinical TrendStatus
        trend_status = cls._determine_trend_status(
            prev_status=prev_obs.technical_status,
            current_status=last_obs.technical_status,
            direction=direction,
            rule=rule,
            all_numeric_obs=valid_numeric_obs,
        )

        explanation = cls._generate_explanation(
            analyte=analyte_display,
            direction=direction,
            trend_status=trend_status,
            prev_val=prev_val,
            last_val=last_val,
            unit=unit or "",
            abs_change=abs_change,
            pct_change=pct_change,
        )

        return AnalyteTrendResult(
            analyte=analyte_display,
            canonical_name=canonical_name,
            unit=unit,
            observation_count=len(sorted_obs),
            first_value=first_val,
            last_value=last_val,
            first_date=first_obs.observation_date,
            last_date=last_obs.observation_date,
            absolute_change=abs_change,
            percentage_change=pct_change,
            direction=direction,
            trend_status=trend_status,
            explanation=explanation,
            history_points=history_points,
        )

    @classmethod
    def _determine_trend_status(
        cls,
        prev_status: str,
        current_status: str,
        direction: str,
        rule: AnalyteTrendRule,
        all_numeric_obs: List[ClinicalObservation],
    ) -> str:
        # Check for multi-point fluctuation (>= 3 points)
        if len(all_numeric_obs) >= 3:
            statuses = [o.technical_status for o in all_numeric_obs[-3:]]
            if (statuses[0] == "LOW" and statuses[1] == "NORMAL" and statuses[2] == "LOW") or \
               (statuses[0] == "HIGH" and statuses[1] == "NORMAL" and statuses[2] == "HIGH") or \
               (statuses[0] == "LOW" and statuses[1] == "HIGH" and statuses[2] == "LOW"):
                return TrendStatusEnum.FLUCTUATING.value

        if direction == TrendDirectionEnum.UNCHANGED.value:
            return TrendStatusEnum.STABLE.value

        # Transition: Abnormal -> Normal is Improving
        if prev_status in ("LOW", "HIGH", "CRITICAL_LOW", "CRITICAL_HIGH") and current_status == "NORMAL":
            return TrendStatusEnum.IMPROVING.value

        # Transition: Normal -> Abnormal is Worsening
        if prev_status == "NORMAL" and current_status in ("LOW", "HIGH", "CRITICAL_LOW", "CRITICAL_HIGH"):
            return TrendStatusEnum.WORSENING.value

        # Status remains LOW
        if prev_status in ("LOW", "CRITICAL_LOW") and current_status in ("LOW", "CRITICAL_LOW"):
            if direction == TrendDirectionEnum.INCREASED.value:
                return TrendStatusEnum.IMPROVING.value  # moving upward toward normal
            elif direction == TrendDirectionEnum.DECREASED.value:
                return TrendStatusEnum.WORSENING.value  # dropping deeper into low

        # Status remains HIGH
        if prev_status in ("HIGH", "CRITICAL_HIGH") and current_status in ("HIGH", "CRITICAL_HIGH"):
            if direction == TrendDirectionEnum.DECREASED.value:
                return TrendStatusEnum.IMPROVING.value  # moving downward toward normal
            elif direction == TrendDirectionEnum.INCREASED.value:
                return TrendStatusEnum.WORSENING.value  # climbing higher

        # If both are normal
        if prev_status == "NORMAL" and current_status == "NORMAL":
            return TrendStatusEnum.STABLE.value

        return TrendStatusEnum.STABLE.value

    @classmethod
    def _generate_explanation(
        cls,
        analyte: str,
        direction: str,
        trend_status: str,
        prev_val: Optional[float],
        last_val: Optional[float],
        unit: str,
        abs_change: Optional[float],
        pct_change: Optional[float],
    ) -> str:
        if direction == TrendDirectionEnum.UNCHANGED.value:
            return f"{analyte} levels remained stable ({last_val} {unit}) with no significant change."

        sign = "+" if abs_change and abs_change > 0 else ""
        pct_str = f" ({sign}{pct_change}%)" if pct_change is not None else ""

        if trend_status == TrendStatusEnum.IMPROVING.value:
            return f"{analyte} showed an improving trajectory from {prev_val} to {last_val} {unit} ({sign}{abs_change} {unit}{pct_str})."
        elif trend_status == TrendStatusEnum.WORSENING.value:
            return f"{analyte} shifted from {prev_val} to {last_val} {unit} ({sign}{abs_change} {unit}{pct_str}), indicating an abnormal or unfavorable trajectory."
        elif trend_status == TrendStatusEnum.FLUCTUATING.value:
            return f"{analyte} values demonstrated multi-visit fluctuation between visits."
        else:
            return f"{analyte} changed from {prev_val} to {last_val} {unit} ({sign}{abs_change} {unit}{pct_str})."
