import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class MedicalRecord(Base, TimestampMixin):
    __tablename__ = "medical_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    clinician_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    encounter_type: Mapped[str] = mapped_column(String(50), default="OPD", nullable=False)  # OPD, IPD, EMERGENCY, LAB_VISIT
    chief_complaint: Mapped[str] = mapped_column(Text, nullable=True)
    clinical_notes: Mapped[str] = mapped_column(Text, nullable=True)
    vitals: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="OPEN", nullable=False)  # OPEN, REVIEWED, CLOSED
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="medical_records")
    reports = relationship("Report", back_populates="medical_record", cascade="all, delete-orphan")
