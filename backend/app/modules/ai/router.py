from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user_token
from app.modules.ai.schemas import (
    AIJobResponse,
    AIJobTriggerRequest,
    AIPipelineStatusResponse,
    DoctorVerificationRequest,
)
from app.modules.ai.service import AIService

router = APIRouter()


@router.get("/status", response_model=AIPipelineStatusResponse)
async def get_pipeline_status():
    """Retrieve Phase 0 pipeline status and active modality readiness."""
    return AIPipelineStatusResponse(
        pipeline_status="PHASE_0_ACTIVE",
        ready_for_models=True,
        active_modalities=["blood_report", "prescription", "xray", "sonography", "lab_general"],
        disclaimer=settings.CDSS_DISCLAIMER,
    )


@router.post("/trigger", response_model=AIJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_document_analysis(
    payload: AIJobTriggerRequest,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    """Trigger CDSS structured extraction pipeline for a report."""
    service = AIService(db)
    return await service.trigger_analysis(payload.report_id)


@router.get("/report/{report_id}", response_model=List[AIJobResponse])
async def list_report_ai_jobs(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = AIService(db)
    return await service.list_by_report(report_id)


@router.post("/verify/{job_id}", response_model=AIJobResponse)
async def doctor_verify_ai_insights(
    job_id: str,
    payload: DoctorVerificationRequest,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """Doctor verification workbench endpoint ensuring Human-in-the-Loop compliance."""
    service = AIService(db)
    clinician_id = token.get("sub", "00000000-0000-0000-0000-000000000001")
    return await service.verify_insights(job_id, clinician_id, payload)
