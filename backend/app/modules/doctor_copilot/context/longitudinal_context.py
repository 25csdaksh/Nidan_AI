from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.modules.clinical_intelligence.models import (
    LongitudinalAnalysis,
    LongitudinalTrend,
    LongitudinalSummarySection,
)
from app.modules.doctor_copilot.schemas import EvidenceItem, EvidenceType


async def build_longitudinal_context(
    session: AsyncSession,
    patient_id: str,
) -> Dict[str, Any]:
    """
    Retrieves latest longitudinal analysis, analyte trends, and dynamics classifications.
    """
    # Fetch most recent longitudinal analysis
    ana_stmt = (
        select(LongitudinalAnalysis)
        .where(LongitudinalAnalysis.patient_id == patient_id)
        .order_by(desc(LongitudinalAnalysis.created_at))
        .limit(1)
    )
    ana_res = await session.execute(ana_stmt)
    latest_analysis = ana_res.scalar_one_or_none()

    if not latest_analysis:
        return {
            "analysis_available": False,
            "trends": [],
            "summary_sections": [],
            "evidence_items": [],
        }

    # Fetch trends for this analysis
    trend_stmt = (
        select(LongitudinalTrend)
        .where(LongitudinalTrend.analysis_id == latest_analysis.id)
        .order_by(LongitudinalTrend.canonical_name)
    )
    trend_res = await session.execute(trend_stmt)
    trends = trend_res.scalars().all()

    evidence_items: List[EvidenceItem] = []
    formatted_trends: List[Dict[str, Any]] = []

    for idx, trend in enumerate(trends):
        ev_id = f"EVID-TREND-{idx+1}"
        change_pct = f"{trend.percentage_change:+.1f}%" if trend.percentage_change is not None else "N/A"
        
        evidence_items.append(
            EvidenceItem(
                evidence_id=ev_id,
                type=EvidenceType.LONGITUDINAL_TREND,
                patient_id=patient_id,
                title=f"Trend: {trend.canonical_name} ({trend.direction})",
                value=f"First: {trend.first_value}, Latest: {trend.last_value} ({change_pct})",
                status=trend.trend_status,
                severity=trend.dynamics_classification,
                details={
                    "analyte": trend.analyte,
                    "canonical_name": trend.canonical_name,
                    "direction": trend.direction,
                    "trend_status": trend.trend_status,
                    "dynamics_classification": trend.dynamics_classification,
                    "persistence_count": trend.persistence_count,
                    "history_points": trend.history_points,
                }
            )
        )
        formatted_trends.append({
            "evidence_id": ev_id,
            "id": trend.id,
            "analyte": trend.analyte,
            "canonical_name": trend.canonical_name,
            "direction": trend.direction,
            "trend_status": trend.trend_status,
            "dynamics_classification": trend.dynamics_classification,
            "first_value": trend.first_value,
            "last_value": trend.last_value,
            "absolute_change": trend.absolute_change,
            "percentage_change": trend.percentage_change,
            "persistence_count": trend.persistence_count,
            "history_points": trend.history_points,
        })

    return {
        "analysis_available": True,
        "analysis_id": latest_analysis.id,
        "observation_count": latest_analysis.observation_count,
        "visit_count": latest_analysis.visit_count,
        "start_date": latest_analysis.start_date.strftime("%Y-%m-%d") if latest_analysis.start_date else None,
        "end_date": latest_analysis.end_date.strftime("%Y-%m-%d") if latest_analysis.end_date else None,
        "summary_text": latest_analysis.summary_text,
        "trends": formatted_trends,
        "evidence_items": evidence_items,
    }
