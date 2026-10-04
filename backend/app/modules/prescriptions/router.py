from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_token
from app.modules.prescriptions.schemas import (
    PrescriptionCreate,
    PrescriptionResponse,
    PrescriptionUpdate,
)
from app.modules.prescriptions.service import PrescriptionService

router = APIRouter()


@router.get("/patient/{patient_id}", response_model=List[PrescriptionResponse])
async def list_patient_prescriptions(
    patient_id: str,
    only_active: bool = Query(False, description="Filter only currently active medications"),
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = PrescriptionService(db)
    return await service.list_by_patient(patient_id, only_active=only_active)


@router.post("/", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    payload: PrescriptionCreate,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = PrescriptionService(db)
    return await service.create_prescription(payload)


@router.patch("/{rx_id}", response_model=PrescriptionResponse)
async def update_prescription(
    rx_id: str,
    payload: PrescriptionUpdate,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = PrescriptionService(db)
    return await service.update_prescription(rx_id, payload)
