import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class DocumentTypeEnum(str, enum.Enum):
    UNKNOWN = "UNKNOWN"
    BLOOD_REPORT = "BLOOD_REPORT"
    PRESCRIPTION = "PRESCRIPTION"
    XRAY = "XRAY"
    SONOGRAPHY = "SONOGRAPHY"
    OTHER = "OTHER"


class ProcessingStatusEnum(str, enum.Enum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    STORED = "STORED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class ExtractionStatusEnum(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEWED = "REVIEWED"
    FAILED = "FAILED"


class EntityReviewStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EDITED = "EDITED"
    REJECTED = "REJECTED"


class TechnicalStatusEnum(str, enum.Enum):
    BELOW_REPORTED_RANGE = "BELOW_REPORTED_RANGE"
    WITHIN_REPORTED_RANGE = "WITHIN_REPORTED_RANGE"
    ABOVE_REPORTED_RANGE = "ABOVE_REPORTED_RANGE"
    UNKNOWN = "UNKNOWN"


class MedicalDocument(Base, TimestampMixin):
    __tablename__ = "medical_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), default=DocumentTypeEnum.UNKNOWN.value, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(50), default=ProcessingStatusEnum.UPLOADED.value, nullable=False, index=True)
    processing_error: Mapped[str] = mapped_column(Text, nullable=True)
    storage_provider: Mapped[str] = mapped_column(String(50), default="local", nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="medical_documents")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    extractions = relationship("DocumentExtraction", back_populates="document", cascade="all, delete-orphan")
    entities = relationship("DocumentExtractionEntity", back_populates="document", cascade="all, delete-orphan")


class DocumentExtraction(Base, TimestampMixin):
    __tablename__ = "document_extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("medical_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    extraction_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), default="local_pdf", nullable=False)
    provider_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=ExtractionStatusEnum.NOT_STARTED.value, nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=True)
    raw_blocks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    raw_tables: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    language: Mapped[str] = mapped_column(String(20), default="en", nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    document = relationship("MedicalDocument", back_populates="extractions")
    entities = relationship("DocumentExtractionEntity", back_populates="extraction", cascade="all, delete-orphan")


class DocumentExtractionEntity(Base, TimestampMixin):
    __tablename__ = "document_extraction_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    extraction_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_extractions.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("medical_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), default="LAB_ANALYTE", nullable=False)
    raw_name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value_text: Mapped[str] = mapped_column(String(100), nullable=False)
    numeric_value: Mapped[float] = mapped_column(nullable=True, index=True)
    original_unit: Mapped[str] = mapped_column(String(50), nullable=True)
    normalized_unit: Mapped[str] = mapped_column(String(50), nullable=True)
    reference_range_text: Mapped[str] = mapped_column(String(100), nullable=True)
    reference_min: Mapped[float] = mapped_column(nullable=True)
    reference_max: Mapped[float] = mapped_column(nullable=True)
    technical_status: Mapped[str] = mapped_column(String(50), default=TechnicalStatusEnum.UNKNOWN.value, nullable=False)
    confidence: Mapped[float] = mapped_column(default=1.0, nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    bounding_box: Mapped[dict] = mapped_column(JSON, nullable=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(50), default=EntityReviewStatusEnum.PENDING.value, nullable=False, index=True)
    reviewed_value: Mapped[str] = mapped_column(String(100), nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    extraction = relationship("DocumentExtraction", back_populates="entities")
    document = relationship("MedicalDocument", back_populates="entities")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

