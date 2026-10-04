"""Pydantic v2 Schemas for Prescription Intelligence & Medication Safety (Phase 5)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.modules.prescription_intelligence.models import (
    MedicationReviewStatusEnum,
    PrescriptionStatusEnum,
    SafetyFindingTypeEnum,
    SafetySeverityEnum,
)


class PrescriptionMedicationBase(BaseModel):
    raw_medication_name: str
    canonical_medication_name: str
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None
    strength_value: Optional[float] = None
    strength_unit: Optional[str] = None
    dosage_form: Optional[str] = None
    route: Optional[str] = None
    frequency_code: Optional[str] = None
    frequency_text: Optional[str] = None
    dose_quantity: Optional[str] = None
    duration_value: Optional[int] = None
    duration_unit: Optional[str] = None
    instruction_text: Optional[str] = None
    is_prn: bool = False
    confidence: float = 1.0
    source_text: Optional[str] = None
    page_number: int = 1
    bounding_box: Optional[Dict[str, Any]] = None


class PrescriptionMedicationResponse(PrescriptionMedicationBase):
    id: str
    prescription_id: str
    patient_id: str
    review_status: str = MedicationReviewStatusEnum.PENDING.value
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicationSafetyFindingResponse(BaseModel):
    id: str
    patient_id: str
    prescription_id: Optional[str] = None
    medication_id: Optional[str] = None
    finding_type: str
    severity: str
    title: str
    description: str
    clinical_association: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    rule_id: Optional[str] = None
    rule_version: str = "1.0.0"
    requires_review: bool = True
    review_status: str = MedicationReviewStatusEnum.PENDING.value
    clinician_note: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrescriptionResponse(BaseModel):
    id: str
    patient_id: str
    document_id: Optional[str] = None
    prescriber_name: Optional[str] = None
    prescription_date: Optional[datetime] = None
    source_confidence: float = 1.0
    status: str = PrescriptionStatusEnum.ACTIVE.value
    medications: List[PrescriptionMedicationResponse] = Field(default_factory=list)
    safety_findings: List[MedicationSafetyFindingResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicationTimelineEvent(BaseModel):
    prescription_id: str
    document_id: Optional[str] = None
    prescriber_name: Optional[str] = None
    prescription_date: Optional[datetime] = None
    medications: List[PrescriptionMedicationResponse] = Field(default_factory=list)
    safety_alert_count: int = 0


class PatientMedicationTimelineResponse(BaseModel):
    patient_id: str
    total_prescriptions: int
    total_medications: int
    events: List[MedicationTimelineEvent] = Field(default_factory=list)
    active_medications_summary: List[str] = Field(default_factory=list)


class MedicationSafetyAnalysisRequest(BaseModel):
    include_allergies: bool = True
    include_lab_context: bool = True
    include_duplicates: bool = True
    include_ddi: bool = True
    include_contraindications: bool = True


class MedicationSafetyAnalysisResponse(BaseModel):
    patient_id: str
    prescriptions_analyzed: int
    medications_analyzed: int
    findings: List[MedicationSafetyFindingResponse] = Field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    moderate_count: int = 0
    info_count: int = 0
    pending_review_count: int = 0
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


class MedicationReviewRequest(BaseModel):
    review_status: str  # ACCEPTED, MODIFIED, REJECTED
    clinician_note: Optional[str] = None
    modified_medication_name: Optional[str] = None


class MedicationReviewResponse(BaseModel):
    finding_id: str
    review_status: str
    clinician_note: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicationRuleResponse(BaseModel):
    rule_id: str
    rule_type: str  # DDI, ALLERGY, LAB_CONTEXT, CONTRAINDICATION
    drug_a: Optional[str] = None
    drug_b: Optional[str] = None
    medication: Optional[str] = None
    severity: str
    title: str
    description: str
    clinical_association: Optional[str] = None
    evidence_source: str
    rule_version: str = "1.0.0"
    active: bool = True
