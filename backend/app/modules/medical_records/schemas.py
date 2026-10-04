from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MedicalRecordBase(BaseModel):
    patient_id: str
    clinician_id: Optional[str] = None
    encounter_type: str = "OPD"
    chief_complaint: Optional[str] = None
    clinical_notes: Optional[str] = None
    vitals: Dict[str, Any] = Field(default_factory=dict)
    status: str = "OPEN"


class MedicalRecordCreate(MedicalRecordBase):
    pass


class MedicalRecordUpdate(BaseModel):
    encounter_type: Optional[str] = None
    chief_complaint: Optional[str] = None
    clinical_notes: Optional[str] = None
    vitals: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class MedicalRecordResponse(MedicalRecordBase):
    id: str
    recorded_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
