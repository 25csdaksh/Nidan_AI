from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.modules.clinical_intelligence.models import (
    FindingTypeEnum,
    FindingStatusEnum,
    FindingSeverityEnum,
    FindingReviewStatusEnum,
)


class FindingEvidenceSchema(BaseModel):
    entity_id: Optional[str] = None
    analyte: str
    value: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    status: Optional[str] = None
    page_number: Optional[int] = None
    source_text: Optional[str] = None
    confidence: float = 1.0
    review_status: str = "PENDING"


class ClinicalFindingResponse(BaseModel):
    id: str
    analysis_id: str
    patient_id: str
    document_id: str
    extraction_id: str
    entity_id: Optional[str] = None
    finding_type: str
    analyte: Optional[str] = None
    value: Optional[str] = None
    normalized_value: Optional[float] = None
    unit: Optional[str] = None
    status: str
    severity: str
    title: str
    explanation: str
    clinical_association: Optional[str] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float
    rule_id: str
    rule_version: str
    reference_source: str
    reference_source_version: Optional[str] = None
    requires_review: bool
    review_status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reviewer_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ClinicalAnalysisResponse(BaseModel):
    id: str
    patient_id: str
    document_id: str
    extraction_id: str
    analysis_version: int
    rule_set_version: str
    reference_range_version: str
    status: str
    findings_count: int
    abnormal_count: int
    critical_count: int
    pattern_count: int
    summary_metadata: Dict[str, Any] = Field(default_factory=dict)
    findings: List[ClinicalFindingResponse] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FindingReviewRequest(BaseModel):
    review_status: FindingReviewStatusEnum = Field(..., description="ACCEPT, MODIFY, or REJECT")
    modified_title: Optional[str] = None
    modified_explanation: Optional[str] = None
    reviewer_notes: Optional[str] = None


class ClinicalRuleMetadataResponse(BaseModel):
    rule_id: str
    rule_name: str
    rule_version: str
    rule_type: str
    applicable_analytes: List[str]
    severity: str
    source: str
    source_version: str
    enabled: bool


class LongitudinalDataPoint(BaseModel):
    date: str
    document_id: str
    value: Optional[float] = None
    unit: Optional[str] = None
    status: str
    severity: str


class LongitudinalAnalyteSeries(BaseModel):
    analyte: str
    unit: Optional[str] = None
    data_points: List[LongitudinalDataPoint] = Field(default_factory=list)


class PatientLongitudinalResponse(BaseModel):
    patient_id: str
    analytes: List[LongitudinalAnalyteSeries] = Field(default_factory=list)
    total_observations: int = 0


# -------------------------------------------------------------
# Phase 4: Longitudinal Intelligence API Schemas
# -------------------------------------------------------------

class ClinicalObservationResponse(BaseModel):
    id: str
    patient_id: str
    document_id: str
    extraction_id: str
    entity_id: Optional[str] = None
    analyte: str
    canonical_name: str
    value: str
    normalized_value: Optional[float] = None
    unit: Optional[str] = None
    observation_date: Optional[datetime] = None
    observation_date_source: str
    date_confidence: str
    document_date: Optional[datetime] = None
    technical_status: str
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    reference_source: str
    extraction_confidence: float
    finding_confidence: float
    source_text: Optional[str] = None
    page_number: int
    is_doctor_verified: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LongitudinalTrendResponse(BaseModel):
    id: str
    analysis_id: str
    patient_id: str
    analyte: str
    canonical_name: str
    unit: Optional[str] = None
    direction: str
    trend_status: str
    dynamics_classification: str
    observation_count: int
    first_value: Optional[float] = None
    last_value: Optional[float] = None
    first_date: Optional[datetime] = None
    last_date: Optional[datetime] = None
    absolute_change: Optional[float] = None
    percentage_change: Optional[float] = None
    persistence_count: int
    history_points: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class LongitudinalSummarySectionResponse(BaseModel):
    id: str
    analysis_id: str
    patient_id: str
    section_type: str
    title: str
    generated_text: str
    evidence_ids: List[str] = Field(default_factory=list)
    source_documents: List[str] = Field(default_factory=list)
    source_entities: List[str] = Field(default_factory=list)
    generated_by: str
    generation_version: str
    safety_validation_status: str

    model_config = ConfigDict(from_attributes=True)


class LongitudinalAnalysisRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    analytes: Optional[List[str]] = None
    include_patterns: bool = True
    force_reanalyze: bool = False


class LongitudinalAnalysisResponse(BaseModel):
    id: str
    patient_id: str
    analysis_version: int
    trend_rule_version: str
    summary_version: str
    observation_count: int
    visit_count: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    summary_text: Optional[str] = None
    trends: List[LongitudinalTrendResponse] = Field(default_factory=list)
    sections: List[LongitudinalSummarySectionResponse] = Field(default_factory=list)
    persistent_abnormalities: List[Dict[str, Any]] = Field(default_factory=list)
    new_abnormalities: List[Dict[str, Any]] = Field(default_factory=list)
    resolved_abnormalities: List[Dict[str, Any]] = Field(default_factory=list)
    recurring_abnormalities: List[Dict[str, Any]] = Field(default_factory=list)
    fluctuations: List[Dict[str, Any]] = Field(default_factory=list)
    data_quality_warnings: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LongitudinalReviewNoteCreate(BaseModel):
    note: str
    analysis_id: Optional[str] = None


class LongitudinalReviewNoteResponse(BaseModel):
    id: str
    patient_id: str
    analysis_id: Optional[str] = None
    author_id: Optional[str] = None
    note: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TimelineObservationItem(BaseModel):
    observation_id: str
    document_id: str
    analyte: str
    value: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    status: str
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    observation_date: Optional[str] = None
    date_source: str
    date_confidence: str
    is_doctor_verified: bool


class TimelineVisitGroup(BaseModel):
    document_id: str
    document_type: str
    visit_date: str
    date_source: str
    observations: List[TimelineObservationItem] = Field(default_factory=list)


class PatientTimelineResponse(BaseModel):
    patient_id: str
    total_visits: int
    total_observations: int
    visits: List[TimelineVisitGroup] = Field(default_factory=list)


class VisitComparisonRequest(BaseModel):
    visit_a_document_id: str
    visit_b_document_id: str


class VisitComparisonItemResponse(BaseModel):
    analyte: str
    canonical_name: str
    unit: Optional[str] = None
    visit_a_value: Optional[float] = None
    visit_a_raw_value: Optional[str] = None
    visit_a_status: Optional[str] = None
    visit_b_value: Optional[float] = None
    visit_b_raw_value: Optional[str] = None
    visit_b_status: Optional[str] = None
    absolute_change: Optional[float] = None
    percentage_change: Optional[float] = None
    status_transition: str
    direction: str


class CrossVisitComparisonResponse(BaseModel):
    patient_id: str
    visit_a_document_id: str
    visit_a_date: Optional[str] = None
    visit_b_document_id: str
    visit_b_date: Optional[str] = None
    common_analytes_count: int
    items: List[VisitComparisonItemResponse] = Field(default_factory=list)


