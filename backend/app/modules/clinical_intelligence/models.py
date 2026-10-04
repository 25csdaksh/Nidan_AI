import enum
import uuid
from datetime import datetime
from sqlalchemy import (
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


class FindingTypeEnum(str, enum.Enum):
    ABNORMAL_LAB = "ABNORMAL_LAB"
    CRITICAL_LAB = "CRITICAL_LAB"
    POSSIBLE_DEFICIENCY = "POSSIBLE_DEFICIENCY"
    PATTERN = "PATTERN"
    DATA_QUALITY_WARNING = "DATA_QUALITY_WARNING"


class FindingStatusEnum(str, enum.Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    HIGH = "HIGH"
    CRITICAL_LOW = "CRITICAL_LOW"
    CRITICAL_HIGH = "CRITICAL_HIGH"
    UNKNOWN = "UNKNOWN"
    REFERENCE_RANGE_UNRESOLVED = "REFERENCE_RANGE_UNRESOLVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class FindingSeverityEnum(str, enum.Enum):
    INFO = "INFO"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingReviewStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"


class ReferenceRange(Base, TimestampMixin):
    __tablename__ = "reference_ranges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analyte: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    panel: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sex: Mapped[str] = mapped_column(String(20), default="all", nullable=False, index=True)  # male, female, all
    age_min: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    age_max: Mapped[float] = mapped_column(Float, default=120.0, nullable=False)
    pregnancy_status: Mapped[str] = mapped_column(String(30), default="all", nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    lower_bound: Mapped[float] = mapped_column(Float, nullable=True)
    upper_bound: Mapped[float] = mapped_column(Float, nullable=True)
    lower_operator: Mapped[str] = mapped_column(String(10), default=">=", nullable=False)
    upper_operator: Mapped[str] = mapped_column(String(10), default="<=", nullable=False)
    critical_low: Mapped[float] = mapped_column(Float, nullable=True)
    critical_high: Mapped[float] = mapped_column(Float, nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_version: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=True)
    effective_from: Mapped[str] = mapped_column(String(50), default="2026-01-01", nullable=False)
    effective_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)


class ClinicalAnalysis(Base, TimestampMixin):
    __tablename__ = "clinical_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("medical_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    extraction_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_extractions.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    rule_set_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    reference_range_version: Mapped[str] = mapped_column(String(50), default="2026.1", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False, index=True)
    findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    abnormal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pattern_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    patient = relationship("Patient")
    document = relationship("MedicalDocument")
    extraction = relationship("DocumentExtraction")
    findings = relationship("ClinicalFinding", back_populates="analysis", cascade="all, delete-orphan")


class ClinicalFinding(Base, TimestampMixin):
    __tablename__ = "clinical_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinical_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("medical_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    extraction_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_extractions.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_extraction_entities.id", ondelete="SET NULL"), nullable=True, index=True)

    finding_type: Mapped[str] = mapped_column(String(50), default=FindingTypeEnum.ABNORMAL_LAB.value, nullable=False, index=True)
    analyte: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    value: Mapped[str] = mapped_column(String(100), nullable=True)
    normalized_value: Mapped[float] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=FindingStatusEnum.NORMAL.value, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), default=FindingSeverityEnum.INFO.value, nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    clinical_association: Mapped[str] = mapped_column(Text, nullable=True)
    evidence: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    rule_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rule_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    reference_source: Mapped[str] = mapped_column(String(50), default="KNOWLEDGE_BASE", nullable=False)
    reference_source_version: Mapped[str] = mapped_column(String(100), nullable=True)

    requires_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    review_status: Mapped[str] = mapped_column(String(50), default=FindingReviewStatusEnum.PENDING.value, nullable=False, index=True)
    reviewed_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    analysis = relationship("ClinicalAnalysis", back_populates="findings")
    patient = relationship("Patient")
    document = relationship("MedicalDocument")
    entity = relationship("DocumentExtractionEntity")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


# -------------------------------------------------------------
# Phase 4: Longitudinal Patient Intelligence Models
# -------------------------------------------------------------

class TrendDirectionEnum(str, enum.Enum):
    INCREASED = "INCREASED"
    DECREASED = "DECREASED"
    UNCHANGED = "UNCHANGED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class TrendStatusEnum(str, enum.Enum):
    IMPROVING = "IMPROVING"
    WORSENING = "WORSENING"
    STABLE = "STABLE"
    FLUCTUATING = "FLUCTUATING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNKNOWN = "UNKNOWN"


class AbnormalityDynamicsEnum(str, enum.Enum):
    NORMAL = "NORMAL"
    PERSISTENT_ABNORMALITY = "PERSISTENT_ABNORMALITY"
    NEW_ABNORMALITY = "NEW_ABNORMALITY"
    RESOLVED_ABNORMALITY = "RESOLVED_ABNORMALITY"
    RECURRING_ABNORMALITY = "RECURRING_ABNORMALITY"
    FLUCTUATING = "FLUCTUATING"
    STABLE = "STABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class SummarySectionTypeEnum(str, enum.Enum):
    OVERVIEW = "OVERVIEW"
    LABORATORY_TRENDS = "LABORATORY_TRENDS"
    PERSISTENT_ABNORMALITIES = "PERSISTENT_ABNORMALITIES"
    NEW_FINDINGS = "NEW_FINDINGS"
    RESOLVED_FINDINGS = "RESOLVED_FINDINGS"
    RECURRING_FINDINGS = "RECURRING_FINDINGS"
    PATTERN_CHANGES = "PATTERN_CHANGES"
    DATA_QUALITY = "DATA_QUALITY"
    DOCTOR_NOTES = "DOCTOR_NOTES"


class ClinicalObservation(Base, TimestampMixin):
    __tablename__ = "clinical_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("medical_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    extraction_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_extractions.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_extraction_entities.id", ondelete="SET NULL"), nullable=True, index=True)

    analyte: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_value: Mapped[float] = mapped_column(Float, nullable=True, index=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)

    observation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    observation_date_source: Mapped[str] = mapped_column(String(50), default="UPLOAD_TIMESTAMP", nullable=False)
    date_confidence: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    document_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    technical_status: Mapped[str] = mapped_column(String(50), default=FindingStatusEnum.NORMAL.value, nullable=False, index=True)
    reference_min: Mapped[float] = mapped_column(Float, nullable=True)
    reference_max: Mapped[float] = mapped_column(Float, nullable=True)
    reference_source: Mapped[str] = mapped_column(String(50), default="REPORT", nullable=False)

    extraction_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    finding_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_doctor_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    patient = relationship("Patient")
    document = relationship("MedicalDocument")
    extraction = relationship("DocumentExtraction")
    entity = relationship("DocumentExtractionEntity")


class LongitudinalAnalysis(Base, TimestampMixin):
    __tablename__ = "longitudinal_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    trend_rule_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    summary_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    visit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_text: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    patient = relationship("Patient")
    trends = relationship("LongitudinalTrend", back_populates="analysis", cascade="all, delete-orphan")
    sections = relationship("LongitudinalSummarySection", back_populates="analysis", cascade="all, delete-orphan")
    notes = relationship("LongitudinalReviewNote", back_populates="analysis", cascade="all, delete-orphan")


class LongitudinalTrend(Base, TimestampMixin):
    __tablename__ = "longitudinal_trends"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("longitudinal_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    analyte: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)

    direction: Mapped[str] = mapped_column(String(50), default=TrendDirectionEnum.UNCHANGED.value, nullable=False, index=True)
    trend_status: Mapped[str] = mapped_column(String(50), default=TrendStatusEnum.STABLE.value, nullable=False, index=True)
    dynamics_classification: Mapped[str] = mapped_column(String(50), default=AbnormalityDynamicsEnum.NORMAL.value, nullable=False, index=True)
    observation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    first_value: Mapped[float] = mapped_column(Float, nullable=True)
    last_value: Mapped[float] = mapped_column(Float, nullable=True)
    first_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    absolute_change: Mapped[float] = mapped_column(Float, nullable=True)
    percentage_change: Mapped[float] = mapped_column(Float, nullable=True)
    persistence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    history_points: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Relationships
    analysis = relationship("LongitudinalAnalysis", back_populates="trends")
    patient = relationship("Patient")


class LongitudinalSummarySection(Base, TimestampMixin):
    __tablename__ = "longitudinal_summary_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("longitudinal_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)

    section_type: Mapped[str] = mapped_column(String(50), default=SummarySectionTypeEnum.OVERVIEW.value, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    source_documents: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    source_entities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(50), default="DETERMINISTIC_ENGINE", nullable=False)
    generation_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    safety_validation_status: Mapped[str] = mapped_column(String(50), default="PASSED", nullable=False)

    # Relationships
    analysis = relationship("LongitudinalAnalysis", back_populates="sections")
    patient = relationship("Patient")


class LongitudinalReviewNote(Base, TimestampMixin):
    __tablename__ = "longitudinal_review_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("longitudinal_analyses.id", ondelete="CASCADE"), nullable=True, index=True)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    analysis = relationship("LongitudinalAnalysis", back_populates="notes")
    patient = relationship("Patient")
    author = relationship("User", foreign_keys=[author_id])

