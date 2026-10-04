from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.modules.reports.models import DocumentType, ExtractionStatus


class ReportBase(BaseModel):
    patient_id: str
    medical_record_id: Optional[str] = None
    document_type: DocumentType = DocumentType.BLOOD_REPORT
    file_name: str
    mime_type: str
    file_size_bytes: int


class ReportCreate(ReportBase):
    storage_key: str
    checksum_sha256: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class ReportUpdate(BaseModel):
    extraction_status: Optional[ExtractionStatus] = None
    raw_extracted_text: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class ReportResponse(ReportBase):
    id: str
    storage_key: str
    checksum_sha256: str
    extraction_status: ExtractionStatus
    metadata_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportUploadResponse(BaseModel):
    report: ReportResponse
    task_id: Optional[str] = None
    message: str
