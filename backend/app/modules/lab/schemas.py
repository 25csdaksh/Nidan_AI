from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class LabResultBase(BaseModel):
    patient_id: str
    report_id: str
    panel_name: str = "General"
    analyte_name: str
    loinc_code: Optional[str] = None
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    interpretation: Optional[str] = None
    is_abnormal: bool = False
    is_critical: bool = False


class LabResultCreate(LabResultBase):
    pass


class LabResultResponse(LabResultBase):
    id: str
    recorded_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabTrendItem(BaseModel):
    recorded_at: datetime
    value: float
    unit: Optional[str]
    is_abnormal: bool


class LabTrendResponse(BaseModel):
    patient_id: str
    analyte_name: str
    unit: Optional[str]
    ref_low: Optional[float]
    ref_high: Optional[float]
    trends: List[LabTrendItem]
