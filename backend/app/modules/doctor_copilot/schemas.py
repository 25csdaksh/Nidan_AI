from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CopilotRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class QueryType(str, Enum):
    PATIENT_SUMMARY = "PATIENT_SUMMARY"
    LAB_SUMMARY = "LAB_SUMMARY"
    LAB_COMPARISON = "LAB_COMPARISON"
    TREND_QUERY = "TREND_QUERY"
    ABNORMALITY_QUERY = "ABNORMALITY_QUERY"
    MEDICATION_QUERY = "MEDICATION_QUERY"
    MEDICATION_SAFETY_QUERY = "MEDICATION_SAFETY_QUERY"
    PRESCRIPTION_QUERY = "PRESCRIPTION_QUERY"
    DOCUMENT_QUERY = "DOCUMENT_QUERY"
    TIMELINE_QUERY = "TIMELINE_QUERY"
    EVIDENCE_QUERY = "EVIDENCE_QUERY"
    IMAGING_QUERY = "IMAGING_QUERY"
    IMAGING_COMPARISON = "IMAGING_COMPARISON"
    DATA_QUALITY_QUERY = "DATA_QUALITY_QUERY"
    GENERAL_MEDICAL_KNOWLEDGE = "GENERAL_MEDICAL_KNOWLEDGE"
    PROHIBITED_CLINICAL_DECISION = "PROHIBITED_CLINICAL_DECISION"
    UNSUPPORTED_QUERY = "UNSUPPORTED_QUERY"
    GENERAL_QUERY = "GENERAL_QUERY"


class SupportLevel(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


class SafetyStatus(str, Enum):
    PASSED = "PASSED"
    BLOCKED = "BLOCKED"
    FLAGGED = "FLAGGED"
    PROHIBITED_REQUEST = "PROHIBITED_REQUEST"


class FeedbackCategory(str, Enum):
    HELPFUL = "HELPFUL"
    NOT_HELPFUL = "NOT_HELPFUL"
    EVIDENCE_INCORRECT = "EVIDENCE_INCORRECT"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    UNSAFE_WORDING = "UNSAFE_WORDING"
    OTHER = "OTHER"


class EvidenceType(str, Enum):
    LAB_RESULT = "LAB_RESULT"
    CLINICAL_FINDING = "CLINICAL_FINDING"
    LONGITUDINAL_TREND = "LONGITUDINAL_TREND"
    PRESCRIPTION = "PRESCRIPTION"
    MEDICATION = "MEDICATION"
    MEDICATION_SAFETY = "MEDICATION_SAFETY"
    DOCUMENT = "DOCUMENT"
    CLINICIAN_NOTE = "CLINICIAN_NOTE"
    ALLERGY_RECORD = "ALLERGY_RECORD"
    IMAGING_FINDING = "IMAGING_FINDING"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: str
    type: EvidenceType
    patient_id: str
    document_id: Optional[str] = None
    entity_id: Optional[str] = None
    observation_id: Optional[str] = None
    finding_id: Optional[str] = None
    prescription_id: Optional[str] = None
    medication_id: Optional[str] = None
    rule_id: Optional[str] = None
    date: Optional[str] = None
    source_text: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    confidence: Optional[float] = None
    review_status: Optional[str] = None
    title: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ClaimItem(BaseModel):
    claim: str
    evidence_ids: List[str] = Field(default_factory=list)
    support_level: SupportLevel = SupportLevel.SUPPORTED
    validation_note: Optional[str] = None


class StructuredCopilotResponse(BaseModel):
    answer: str
    claims: List[ClaimItem] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    data_quality_notes: List[str] = Field(default_factory=list)
    requires_clinician_review: bool = True
    safety_status: SafetyStatus = SafetyStatus.PASSED
    query_type: QueryType = QueryType.GENERAL_QUERY
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    records_considered: int = 0
    records_included: int = 0
    records_excluded: int = 0
    prompt_version: str = "1.0"
    context_version: str = "1.0"
    safety_version: str = "1.0"
    model_provider: str = "nidan-deterministic"
    model_version: str = "1.0"


class CopilotSessionCreate(BaseModel):
    title: Optional[str] = "Clinical Case Review"
    initial_query: Optional[str] = None


class CopilotSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    clinician_id: Optional[str]
    title: str
    status: str
    context_version: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class CopilotQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000)
    session_id: Optional[str] = None
    filter_analyte: Optional[str] = None
    filter_date_range: Optional[List[str]] = None


class CopilotMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    patient_id: str
    role: str
    content: str
    query_type: str
    structured_response: Dict[str, Any]
    evidence_ids: List[str]
    safety_status: str
    model_provider: str
    model_version: str
    prompt_version: str
    created_at: datetime


class CopilotFeedbackCreate(BaseModel):
    rating: str = Field(..., pattern="^(HELPFUL|NOT_HELPFUL)$")
    feedback_category: FeedbackCategory = FeedbackCategory.HELPFUL
    comments: Optional[str] = None


class CopilotFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str
    clinician_id: Optional[str]
    patient_id: str
    rating: str
    feedback_category: str
    comments: Optional[str]
    created_at: datetime
