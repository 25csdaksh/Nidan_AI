from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import UserRole, get_current_user_token, require_roles
from app.modules.medical_documents.schemas import PaginatedMedicalDocumentsResponse
from app.modules.medical_documents.service import MedicalDocumentService
from app.modules.patients.schemas import PatientCreate, PatientResponse, PatientUpdate
from app.modules.patients.service import PatientService

router = APIRouter()


@router.get("/", response_model=List[PatientResponse])
async def list_patients(
    q: Optional[str] = Query(None, description="Search by MRN, name, or phone"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = PatientService(db)
    return await service.search_patients(query=q, skip=skip, limit=limit)


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    payload: PatientCreate,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = PatientService(db)
    return await service.create_patient(payload)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = PatientService(db)
    return await service.get_by_id(patient_id)


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = PatientService(db)
    return await service.update_patient(patient_id, payload)


@router.get("/{patient_id}/medical-documents", response_model=PaginatedMedicalDocumentsResponse)
async def list_patient_medical_documents(
    patient_id: str,
    document_type: Optional[str] = Query(None, description="Filter by modality (e.g. BLOOD_REPORT, PRESCRIPTION, XRAY, SONOGRAPHY)"),
    processing_status: Optional[str] = Query(None, description="Filter by status (e.g. QUEUED, COMPLETED, FAILED)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_desc: bool = Query(True, description="Sort descending by upload date"),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """List medical documents belonging to a patient with pagination and modality filters."""
    doc_service = MedicalDocumentService(db)
    items, total = await doc_service.list_patient_documents(
        patient_id=patient_id,
        current_user=token,
        document_type=document_type,
        processing_status=processing_status,
        page=page,
        page_size=page_size,
        sort_desc=sort_desc,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedMedicalDocumentsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
