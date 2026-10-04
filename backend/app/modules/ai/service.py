from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import AppException, ResourceNotFoundError
from app.modules.ai.models import AIAnalysisJob
from app.modules.ai.schemas import DoctorVerificationRequest
from app.modules.reports.service import ReportService


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.report_service = ReportService(db)

    async def get_job(self, job_id: str) -> AIAnalysisJob:
        result = await self.db.execute(select(AIAnalysisJob).where(AIAnalysisJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise ResourceNotFoundError(f"AI job record '{job_id}' not found.")
        return job

    async def list_by_report(self, report_id: str) -> List[AIAnalysisJob]:
        stmt = select(AIAnalysisJob).where(AIAnalysisJob.report_id == report_id).order_by(AIAnalysisJob.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def trigger_analysis(self, report_id: str) -> AIAnalysisJob:
        report = await self.report_service.get_by_id(report_id)
        
        # In Phase 0, we create a clean job record acknowledging Phase 0 scaffolding
        job = AIAnalysisJob(
            report_id=report.id,
            status="PHASE_0_READY",
            pipeline_version="0.1.0-phase0-scaffold",
            insights_payload={
                "status": "PHASE_0_ACTIVE",
                "message": "AI analysis pipeline scaffold is prepared for model integration in Phase 1.",
                "disclaimer": settings.CDSS_DISCLAIMER,
                "document_modality": report.document_type,
            },
            doctor_verified=False,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def verify_insights(self, job_id: str, clinician_id: str, data: DoctorVerificationRequest) -> AIAnalysisJob:
        job = await self.get_job(job_id)
        job.doctor_verified = data.approved
        job.verified_by_id = clinician_id
        job.doctor_notes = data.doctor_notes
        job.verified_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(job)
        return job
