from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PrescriptionBase(BaseModel):
    patient_id: str
    report_id: Optional[str] = None
    drug_name: str
    generic_name: Optional[str] = None
    dosage: str
    frequency: str
    route: str = "ORAL"
    duration_days: Optional[int] = None
    instructions: Optional[str] = None
    is_active: bool = True


class PrescriptionCreate(PrescriptionBase):
    pass


class PrescriptionUpdate(BaseModel):
    is_active: Optional[bool] = None
    instructions: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None


class PrescriptionResponse(PrescriptionBase):
    id: str
    prescribed_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
