from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.modules.imaging.models import (
    FindingReviewStatusEnum,
    ImageQualityStatusEnum,
    ModalityEnum,
    ProcessingStatusEnum,
)
from app.modules.imaging.findings.safety import IMAGING_CDSS_DISCLAIMER


class ImagingImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    imaging_study_id: str
    original_filename: str
    mime_type: str
    file_size: int
    sha256_hash: str
    width: int
    height: int
    bit_depth: int
    color_space: str
    orientation: Optional[str] = None
    created_at: datetime


class ImagingFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    imaging_analysis_id: str
    finding_code: str
    finding_name: str
    anatomical_region: str
    probability: float
    confidence: float
    severity: str
    model_threshold: float
    localization_json: Dict[str, Any] = Field(default_factory=dict)
    explanation: str
    evidence_json: Dict[str, Any] = Field(default_factory=dict)
    review_status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    clinician_comment: Optional[str] = None
    created_at: datetime


class ImagingFindingReviewRequest(BaseModel):
    review_status: FindingReviewStatusEnum
    clinician_comment: Optional[str] = Field(None, max_length=1000)
    modified_severity: Optional[str] = None


class ImagingAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    imaging_study_id: str
    model_id: str
    model_version: str
    preprocessing_version: str
    inference_version: str
    threshold_version: str
    calibration_version: str
    status: str
    image_quality_status: str
    input_hash: str
    output_json: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    findings: List[ImagingFindingResponse] = Field(default_factory=list)


class ImagingStudyCreate(BaseModel):
    patient_id: str
    medical_document_id: Optional[str] = None
    modality: ModalityEnum = ModalityEnum.XRAY
    body_part: str = "CHEST"
    view_position: Optional[str] = "PA"
    study_date: Optional[datetime] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class ImagingStudyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    medical_document_id: Optional[str] = None
    modality: str
    body_part: str
    view_position: Optional[str] = None
    study_date: datetime
    acquisition_date: Optional[datetime] = None
    image_count: int
    image_quality_status: str
    processing_status: str
    current_analysis_id: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    cdss_disclaimer: str = IMAGING_CDSS_DISCLAIMER


class ImagingStudyDetailResponse(ImagingStudyResponse):
    images: List[ImagingImageResponse] = Field(default_factory=list)
    analyses: List[ImagingAnalysisResponse] = Field(default_factory=list)
    active_findings: List[ImagingFindingResponse] = Field(default_factory=list)


class ImagingTimelineItem(BaseModel):
    study_id: str
    study_date: datetime
    modality: str
    body_part: str
    view_position: Optional[str] = None
    analysis_id: Optional[str] = None
    model_version: Optional[str] = None
    processing_status: str
    image_quality_status: str
    findings_count: int
    key_findings: List[Dict[str, Any]] = Field(default_factory=list)
    review_status_summary: Dict[str, int] = Field(default_factory=dict)


class ImagingTimelineResponse(BaseModel):
    patient_id: str
    total_studies: int
    timeline: List[ImagingTimelineItem] = Field(default_factory=list)
    cdss_disclaimer: str = IMAGING_CDSS_DISCLAIMER


class ImagingExplainabilityResponse(BaseModel):
    analysis_id: str
    method: str
    model_version: str
    target_label: str
    heatmap_grid: List[List[float]]
    localization_boxes: List[Dict[str, Any]]
    disclaimer: str
    generated_at: str


class ImagingModelMetadataResponse(BaseModel):
    model_id: str
    version: str
    modality: str
    framework: str
    input_size: List[int]
    supported_views: List[str]
    labels: List[str]
    training_dataset_reference: str
    intended_use: str
    limitations: List[str]
    threshold_version: str
    calibration_status: str
    calibration_version: str
    is_production_ready: bool
    model_sha256: Optional[str] = None
    model_type: str = "TEST_HARNESS"
    readiness_status: str = "DEMO_TEST_ONLY"
    weights_status: str = "NOT_APPLICABLE"
