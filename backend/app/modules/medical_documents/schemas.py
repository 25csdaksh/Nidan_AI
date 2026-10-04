from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.modules.medical_documents.models import DocumentTypeEnum, ProcessingStatusEnum


class MedicalDocumentBase(BaseModel):
    patient_id: str
    original_filename: str
    document_type: DocumentTypeEnum = DocumentTypeEnum.UNKNOWN
    processing_status: ProcessingStatusEnum = ProcessingStatusEnum.UPLOADED
    mime_type: str
    file_size: int
    sha256_hash: str
    storage_provider: str = "local"
    page_count: Optional[int] = None
    processing_error: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class MedicalDocumentResponse(MedicalDocumentBase):
    id: str
    uploaded_by: Optional[str] = None
    stored_filename: str
    storage_key: str
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DuplicateWarningInfo(BaseModel):
    is_duplicate: bool
    existing_document_id: str
    existing_filename: str
    uploaded_at: datetime
    sha256_hash: str
    message: str


class MedicalDocumentUploadResponse(BaseModel):
    document: MedicalDocumentResponse
    task_id: Optional[str] = None
    duplicate_warning: Optional[DuplicateWarningInfo] = None
    message: str


class MedicalDocumentStatusResponse(BaseModel):
    id: str
    processing_status: ProcessingStatusEnum
    document_type: DocumentTypeEnum
    page_count: Optional[int] = None
    processing_error: Optional[str] = None
    updated_at: datetime
    processed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaginatedMedicalDocumentsResponse(BaseModel):
    items: List[MedicalDocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ExtractionEntityResponse(BaseModel):
    id: str
    extraction_id: str
    document_id: str
    entity_type: str
    raw_name: str
    canonical_name: str
    value_text: str
    numeric_value: Optional[float] = None
    original_unit: Optional[str] = None
    normalized_unit: Optional[str] = None
    reference_range_text: Optional[str] = None
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    technical_status: str
    confidence: float
    page_number: int
    bounding_box: Optional[Dict[str, Any]] = None
    source_text: Optional[str] = None
    review_status: str
    reviewed_value: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentExtractionResponse(BaseModel):
    id: str
    document_id: str
    extraction_version: int
    provider: str
    provider_version: str
    status: str
    raw_text: Optional[str] = None
    raw_blocks: List[Dict[str, Any]] = Field(default_factory=list)
    raw_tables: List[Dict[str, Any]] = Field(default_factory=list)
    language: str
    page_count: int
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None
    entities: List[ExtractionEntityResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewEntityRequest(BaseModel):
    review_status: str = Field(..., description="ACCEPTED, EDITED, or REJECTED")
    reviewed_value: Optional[str] = Field(None, description="Corrected value if status is EDITED")
    reviewed_unit: Optional[str] = Field(None, description="Corrected unit if status is EDITED")


class PaginatedEntitiesResponse(BaseModel):
    items: List[ExtractionEntityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

