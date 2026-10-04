import enum
import uuid
from sqlalchemy import BigInteger, Enum as SQLEnum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class DocumentType(str, enum.Enum):
    BLOOD_REPORT = "blood_report"
    PRESCRIPTION = "prescription"
    XRAY = "xray"
    SONOGRAPHY = "sonography"
    LAB_GENERAL = "lab_general"
    OTHER = "other"


class ExtractionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DOCTOR_VERIFIED = "DOCTOR_VERIFIED"


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    medical_record_id: Mapped[str] = mapped_column(String(36), ForeignKey("medical_records.id", ondelete="SET NULL"), nullable=True)
    document_type: Mapped[str] = mapped_column(String(50), default=DocumentType.BLOOD_REPORT.value, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_status: Mapped[str] = mapped_column(String(50), default=ExtractionStatus.PENDING.value, nullable=False)
    raw_extracted_text: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="reports")
    medical_record = relationship("MedicalRecord", back_populates="reports")
    lab_results = relationship("LabResult", back_populates="report", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="report", cascade="all, delete-orphan")
    imaging_studies = relationship("ImagingStudy", back_populates="report", cascade="all, delete-orphan")
    ai_jobs = relationship("AIAnalysisJob", back_populates="report", cascade="all, delete-orphan")
