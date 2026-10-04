from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.modules.clinical_intelligence.models import ClinicalObservation, ClinicalFinding
from app.modules.doctor_copilot.schemas import EvidenceItem, EvidenceType


async def build_laboratory_context(
    session: AsyncSession,
    patient_id: str,
    limit_observations: int = 100,
    limit_findings: int = 50,
) -> Dict[str, Any]:
    """
    Retrieves prioritized laboratory observations and clinical findings with full provenance.
    """
    # 1. Fetch observations ordered by date descending
    obs_stmt = (
        select(ClinicalObservation)
        .where(ClinicalObservation.patient_id == patient_id)
        .order_by(desc(ClinicalObservation.observation_date), desc(ClinicalObservation.created_at))
        .limit(limit_observations)
    )
    obs_res = await session.execute(obs_stmt)
    observations = obs_res.scalars().all()

    # 2. Fetch clinical findings
    find_stmt = (
        select(ClinicalFinding)
        .where(ClinicalFinding.patient_id == patient_id)
        .order_by(desc(ClinicalFinding.created_at))
        .limit(limit_findings)
    )
    find_res = await session.execute(find_stmt)
    findings = find_res.scalars().all()

    evidence_items: List[EvidenceItem] = []
    formatted_observations: List[Dict[str, Any]] = []
    formatted_findings: List[Dict[str, Any]] = []

    for idx, obs in enumerate(observations):
        ev_id = f"EVID-LAB-{idx+1}"
        ref_text = f"{obs.reference_min} - {obs.reference_max}" if (obs.reference_min is not None and obs.reference_max is not None) else None
        
        evidence_items.append(
            EvidenceItem(
                evidence_id=ev_id,
                type=EvidenceType.LAB_RESULT,
                patient_id=patient_id,
                document_id=obs.document_id,
                observation_id=obs.id,
                entity_id=obs.entity_id,
                date=obs.observation_date.strftime("%Y-%m-%d") if obs.observation_date else "UNKNOWN",
                title=f"Lab Observation: {obs.canonical_name}",
                value=str(obs.value),
                unit=obs.unit,
                reference_range=ref_text,
                status=obs.technical_status,
                review_status="VERIFIED" if obs.is_doctor_verified else "EXTRACTED",
                details={
                    "analyte": obs.analyte,
                    "canonical_name": obs.canonical_name,
                    "normalized_value": obs.normalized_value,
                    "date_source": obs.observation_date_source,
                }
            )
        )
        formatted_observations.append({
            "evidence_id": ev_id,
            "id": obs.id,
            "analyte": obs.analyte,
            "canonical_name": obs.canonical_name,
            "value": obs.value,
            "normalized_value": obs.normalized_value,
            "unit": obs.unit,
            "technical_status": obs.technical_status,
            "reference_min": obs.reference_min,
            "reference_max": obs.reference_max,
            "observation_date": obs.observation_date.strftime("%Y-%m-%d") if obs.observation_date else "UNKNOWN",
            "is_doctor_verified": obs.is_doctor_verified,
            "document_id": obs.document_id,
        })

    for idx, find in enumerate(findings):
        ev_id = f"EVID-FIND-{idx+1}"
        evidence_items.append(
            EvidenceItem(
                evidence_id=ev_id,
                type=EvidenceType.CLINICAL_FINDING,
                patient_id=patient_id,
                document_id=find.document_id,
                finding_id=find.id,
                entity_id=find.entity_id,
                rule_id=find.rule_id,
                title=find.title,
                value=str(find.value) if find.value else None,
                unit=find.unit,
                status=find.status,
                severity=find.severity,
                confidence=find.confidence,
                review_status=find.review_status,
                details={
                    "finding_type": find.finding_type,
                    "explanation": find.explanation,
                    "clinical_association": find.clinical_association,
                    "rule_version": find.rule_version,
                }
            )
        )
        formatted_findings.append({
            "evidence_id": ev_id,
            "id": find.id,
            "finding_type": find.finding_type,
            "analyte": find.analyte,
            "title": find.title,
            "severity": find.severity,
            "status": find.status,
            "value": find.value,
            "unit": find.unit,
            "explanation": find.explanation,
            "clinical_association": find.clinical_association,
            "confidence": find.confidence,
            "review_status": find.review_status,
            "document_id": find.document_id,
        })

    return {
        "observations_count": len(formatted_observations),
        "findings_count": len(formatted_findings),
        "observations": formatted_observations,
        "findings": formatted_findings,
        "evidence_items": evidence_items,
    }
