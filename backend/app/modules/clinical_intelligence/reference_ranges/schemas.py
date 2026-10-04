from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReferenceRangeBase(BaseModel):
    analyte: str
    canonical_name: str
    panel: str
    sex: str = "all"  # male, female, all
    age_min: float = 0.0
    age_max: float = 120.0
    pregnancy_status: str = "all"  # all, pregnant, non_pregnant
    unit: str
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    lower_operator: str = ">="
    upper_operator: str = "<="
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    source_name: str
    source_version: str
    source_url: Optional[str] = None
    effective_from: str = "2026-01-01"
    effective_to: Optional[datetime] = None
    version: int = 1
    notes: Optional[str] = None
    is_active: bool = True


class ReferenceRangeCreate(ReferenceRangeBase):
    pass


class ReferenceRangeResponse(ReferenceRangeBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ResolvedReferenceRange(BaseModel):
    analyte: str
    canonical_name: str
    source_type: str  # REPORT, DOCTOR_REVIEWED, KNOWLEDGE_BASE, UNKNOWN
    source_name: Optional[str] = None
    source_version: Optional[str] = None
    resolution_reason: str
    unit: Optional[str] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    is_resolved: bool = True
    raw_reference_text: Optional[str] = None
