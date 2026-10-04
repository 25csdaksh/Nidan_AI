from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_token
from app.modules.imaging.schemas import ImagingStudyCreate, ImagingStudyResponse
from app.modules.imaging.service import ImagingService

router = APIRouter()


@router.get("/patient/{patient_id}", response_model=List[ImagingStudyResponse])
async def list_patient_imaging_studies(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = ImagingService(db)
    return await service.list_by_patient(patient_id)


@router.post("/", response_model=ImagingStudyResponse, status_code=status.HTTP_201_CREATED)
async def create_imaging_study(
    payload: ImagingStudyCreate,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = ImagingService(db)
    return await service.create_study(payload)


@router.get("/{study_id}", response_model=ImagingStudyResponse)
async def get_imaging_study(
    study_id: str,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = ImagingService(db)
    return await service.get_by_id(study_id)
