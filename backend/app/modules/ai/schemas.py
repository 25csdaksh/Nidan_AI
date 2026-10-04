from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.modules.ai.interfaces import ClinicalInsightItem


class AIJobTriggerRequest(BaseModel):
    report_id: str
    modality_override: Optional[str] = None


class DoctorVerificationRequest(BaseModel):
    doctor_notes: Optional[str] = None
    approved: bool = True


class AIJobResponse(BaseModel):
    id: str
    report_id: str
    status: str
    pipeline_version: str
    insights_payload: Dict[str, Any]
    doctor_verified: bool
    verified_by_id: Optional[str] = None
    doctor_notes: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIPipelineStatusResponse(BaseModel):
    pipeline_status: str = "PHASE_0_ACTIVE"
    ready_for_models: bool = True
    active_modalities: List[str] = ["blood_report", "prescription", "xray", "sonography", "lab_general"]
    disclaimer: str
