from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_token
from app.core.storage import get_storage_service
from app.modules.reports.models import DocumentType
from app.modules.reports.schemas import ReportResponse, ReportUploadResponse
from app.modules.reports.service import ReportService

router = APIRouter()


@router.post("/upload", response_model=ReportUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_medical_report(
    patient_id: str = Form(...),
    document_type: DocumentType = Form(DocumentType.BLOOD_REPORT),
    medical_record_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    """Upload a medical document (Blood test, prescription, X-ray, sonography)."""
    file_bytes = await file.read()
    service = ReportService(db)
    report, task_id = await service.ingest_file(
        patient_id=patient_id,
        file_bytes=file_bytes,
        filename=file.filename or "medical_document.pdf",
        content_type=file.content_type or "application/octet-stream",
        document_type=document_type,
        medical_record_id=medical_record_id,
    )
    return ReportUploadResponse(
        report=ReportResponse.model_validate(report),
        task_id=task_id,
        message="Medical document uploaded and queued for background pipeline ingestion.",
    )


@router.get("/recent", response_model=List[ReportResponse])
async def list_recent_reports(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = ReportService(db)
    return await service.list_recent(limit=limit)


@router.get("/patient/{patient_id}", response_model=List[ReportResponse])
async def list_patient_reports(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = ReportService(db)
    return await service.list_by_patient(patient_id)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = ReportService(db)
    return await service.get_by_id(report_id)


@router.get("/file/{storage_key:path}")
async def download_report_file(
    storage_key: str,
    _token: dict = Depends(get_current_user_token),
):
    storage = get_storage_service()
    content = await storage.get_file_bytes(storage_key)
    return Response(content=content, media_type="application/octet-stream")
