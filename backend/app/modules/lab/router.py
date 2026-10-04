from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_token
from app.modules.lab.schemas import LabResultCreate, LabResultResponse, LabTrendResponse
from app.modules.lab.service import LabService

router = APIRouter()


@router.get("/patient/{patient_id}", response_model=List[LabResultResponse])
async def get_patient_lab_results(
    patient_id: str,
    only_abnormal: bool = Query(False, description="Filter only abnormal/flagged laboratory findings"),
    panel_name: Optional[str] = Query(None, description="Filter by panel name (e.g. CBC, LFT, Lipid)"),
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = LabService(db)
    return await service.list_by_patient(patient_id, only_abnormal=only_abnormal, panel_name=panel_name)


@router.get("/report/{report_id}", response_model=List[LabResultResponse])
async def get_report_lab_results(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = LabService(db)
    return await service.list_by_report(report_id)


@router.get("/trends/{patient_id}", response_model=LabTrendResponse)
async def get_analyte_trend(
    patient_id: str,
    analyte: str = Query(..., description="Analyte name to plot longitudinal progression for (e.g. Hemoglobin)"),
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = LabService(db)
    return await service.get_longitudinal_trend(patient_id=patient_id, analyte_name=analyte)


@router.post("/batch", response_model=List[LabResultResponse], status_code=status.HTTP_201_CREATED)
async def batch_record_lab_results(
    payload: List[LabResultCreate],
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = LabService(db)
    return await service.record_batch(payload)
