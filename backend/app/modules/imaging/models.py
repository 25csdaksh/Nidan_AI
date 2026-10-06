import enum
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class ModalityEnum(str, enum.Enum):
    XRAY = "XRAY"
    ULTRASOUND = "ULTRASOUND"
    CT = "CT"
    MRI = "MRI"


class ImageQualityStatusEnum(str, enum.Enum):
    QUALITY_ACCEPTED = "QUALITY_ACCEPTED"
    QUALITY_WARNING = "QUALITY_WARNING"
    QUALITY_REJECTED = "QUALITY_REJECTED"


class ProcessingStatusEnum(str, enum.Enum):
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    PREPROCESSING = "PREPROCESSING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class FindingReviewStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"


class FindingStatusThresholdEnum(str, enum.Enum):
    BELOW_MODEL_THRESHOLD = "BELOW_MODEL_THRESHOLD"
    ABOVE_MODEL_THRESHOLD = "ABOVE_MODEL_THRESHOLD"
    UNCERTAIN = "UNCERTAIN"
    MODEL_ERROR = "MODEL_ERROR"


class ImagingStudy(Base, TimestampMixin):
    __tablename__ = "imaging_studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    medical_document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("medical_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    report_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True)
    modality: Mapped[str] = mapped_column(String(50), default=ModalityEnum.XRAY.value, nullable=False, index=True)
    body_part: Mapped[str] = mapped_column(String(100), default="CHEST", nullable=False)
    view_position: Mapped[Optional[str]] = mapped_column(String(50), default="PA", nullable=True)  # PA, AP, Lateral
    study_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    acquisition_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    image_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    image_quality_status: Mapped[str] = mapped_column(String(50), default=ImageQualityStatusEnum.QUALITY_ACCEPTED.value, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(50), default=ProcessingStatusEnum.QUEUED.value, nullable=False, index=True)
    current_analysis_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    patient = relationship("Patient")
    medical_document = relationship("MedicalDocument")
    report = relationship("Report", back_populates="imaging_studies")
    images = relationship("ImagingImage", back_populates="study", cascade="all, delete-orphan")
    analyses = relationship("ImagingAnalysis", back_populates="study", cascade="all, delete-orphan")


class ImagingImage(Base, TimestampMixin):
    __tablename__ = "imaging_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    imaging_study_id: Mapped[str] = mapped_column(String(36), ForeignKey("imaging_studies.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bit_depth: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    color_space: Mapped[str] = mapped_column(String(50), default="GRAYSCALE", nullable=False)
    orientation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    study = relationship("ImagingStudy", back_populates="images")


class ImagingAnalysis(Base, TimestampMixin):
    __tablename__ = "imaging_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    imaging_study_id: Mapped[str] = mapped_column(String(36), ForeignKey("imaging_studies.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(100), default="XRAY_CHEST_FOUNDATION_V1", nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    preprocessing_version: Mapped[str] = mapped_column(String(50), default="xray-preprocess-v1", nullable=False)
    inference_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    threshold_version: Mapped[str] = mapped_column(String(50), default="xray-thresh-v1", nullable=False)
    calibration_version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=ProcessingStatusEnum.QUEUED.value, nullable=False, index=True)
    image_quality_status: Mapped[str] = mapped_column(String(50), default=ImageQualityStatusEnum.QUALITY_ACCEPTED.value, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    study = relationship("ImagingStudy", back_populates="analyses")
    findings = relationship("ImagingFinding", back_populates="analysis", cascade="all, delete-orphan")


class ImagingFinding(Base, TimestampMixin):
    __tablename__ = "imaging_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    imaging_analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("imaging_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    finding_name: Mapped[str] = mapped_column(String(255), nullable=False)
    anatomical_region: Mapped[str] = mapped_column(String(100), default="LUNG", nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default="MODERATE", nullable=False)
    model_threshold: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    localization_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    review_status: Mapped[str] = mapped_column(String(50), default=FindingReviewStatusEnum.PENDING.value, nullable=False, index=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    clinician_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    analysis = relationship("ImagingAnalysis", back_populates="findings")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
