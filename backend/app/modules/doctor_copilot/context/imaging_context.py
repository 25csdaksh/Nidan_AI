from typing import Any, Dict, List
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.doctor_copilot.schemas import EvidenceItem, EvidenceType
from app.modules.imaging.models import ImagingAnalysis, ImagingFinding, ImagingStudy
from app.modules.imaging.provenance.evidence import build_imaging_evidence_item


async def build_imaging_context(
    session: AsyncSession,
    patient_id: str,
    max_studies: int = 5,
    max_findings: int = 15,
) -> Dict[str, Any]:
    """
    Extracts structured chest X-ray and imaging observations, analysis runs,
    and clinician reviews for inclusion in the Doctor AI Copilot clinical context.
    """
    stmt = (
        select(ImagingStudy)
        .where(ImagingStudy.patient_id == patient_id)
        .options(
            selectinload(ImagingStudy.analyses).selectinload(ImagingAnalysis.findings)
        )
        .order_by(desc(ImagingStudy.study_date))
        .limit(max_studies)
    )
    result = await session.execute(stmt)
    studies = list(result.scalars().all())

    evidence_items: List[EvidenceItem] = []
    recent_studies_data: List[Dict[str, Any]] = []
    recent_findings_data: List[Dict[str, Any]] = []
    accepted_findings_data: List[Dict[str, Any]] = []

    for study in studies:
        latest_analysis = study.analyses[-1] if study.analyses else None
        findings = latest_analysis.findings if latest_analysis else []

        study_dict = {
            "study_id": study.id,
            "modality": study.modality,
            "body_part": study.body_part,
            "view_position": study.view_position,
            "study_date": study.study_date.isoformat() if study.study_date else None,
            "quality_status": study.image_quality_status,
            "processing_status": study.processing_status,
            "findings_count": len(findings),
            "model_version": latest_analysis.model_version if latest_analysis else None,
        }
        recent_studies_data.append(study_dict)

        for finding in findings:
            ev_item = build_imaging_evidence_item(finding, study, latest_analysis)
            evidence_items.append(ev_item)

            finding_dict = {
                "evidence_id": ev_item.evidence_id,
                "finding_code": finding.finding_code,
                "finding_name": finding.finding_name,
                "probability": finding.probability,
                "threshold": finding.model_threshold,
                "severity": finding.severity,
                "review_status": finding.review_status,
                "clinician_comment": finding.clinician_comment,
                "study_date": study.study_date.isoformat() if study.study_date else None,
                "model_version": latest_analysis.model_version if latest_analysis else None,
            }
            recent_findings_data.append(finding_dict)
            if finding.review_status == "ACCEPTED":
                accepted_findings_data.append(finding_dict)

    # Bound evidence items to max_findings
    bounded_evidence = evidence_items[:max_findings]

    return {
        "studies_count": len(studies),
        "recent_studies": recent_studies_data,
        "recent_findings": recent_findings_data[:max_findings],
        "accepted_findings": accepted_findings_data,
        "evidence_items": bounded_evidence,
        "has_imaging": len(studies) > 0,
    }
