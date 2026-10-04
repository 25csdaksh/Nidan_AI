from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_token
from app.modules.medical_records.schemas import (
    MedicalRecordCreate,
    MedicalRecordResponse,
    MedicalRecordUpdate,
)
from app.modules.medical_records.service import MedicalRecordService

router = APIRouter()


@router.get("/patient/{patient_id}", response_model=List[MedicalRecordResponse])
async def list_patient_encounters(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = MedicalRecordService(db)
    return await service.list_by_patient(patient_id)


@router.post("/", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_encounter(
    payload: MedicalRecordCreate,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = MedicalRecordService(db)
    return await service.create_record(payload)


@router.get("/{record_id}", response_model=MedicalRecordResponse)
async def get_encounter(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = MedicalRecordService(db)
    return await service.get_by_id(record_id)


@router.patch("/{record_id}", response_model=MedicalRecordResponse)
async def update_encounter(
    record_id: str,
    payload: MedicalRecordUpdate,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = MedicalRecordService(db)
    return await service.update_record(record_id, payload)
