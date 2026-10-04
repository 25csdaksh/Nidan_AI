from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ImagingStudyBase(BaseModel):
    patient_id: str
    report_id: str
    modality: str = Field(..., description="X-RAY, ULTRASOUND, CT, MRI")
    body_part: str
    view_position: Optional[str] = None
    dicom_series_uid: Optional[str] = None
    radiologist_impression: Optional[str] = None
    structured_findings: Dict[str, Any] = Field(default_factory=dict)


class ImagingStudyCreate(ImagingStudyBase):
    pass


class ImagingStudyResponse(ImagingStudyBase):
    id: str
    performed_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
