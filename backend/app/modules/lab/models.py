import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class LabResult(Base, TimestampMixin):
    __tablename__ = "lab_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    panel_name: Mapped[str] = mapped_column(String(100), default="General", nullable=False)  # CBC, Lipid Profile, LFT, KFT
    analyte_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Hemoglobin, Glucose Fasting, Creatinine
    loinc_code: Mapped[str] = mapped_column(String(20), nullable=True)
    value_numeric: Mapped[float] = mapped_column(Float, nullable=True)
    value_text: Mapped[str] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(30), nullable=True)
    ref_low: Mapped[float] = mapped_column(Float, nullable=True)
    ref_high: Mapped[float] = mapped_column(Float, nullable=True)
    interpretation: Mapped[str] = mapped_column(String(50), nullable=True)  # NORMAL, LOW, HIGH, CRITICAL_LOW, CRITICAL_HIGH
    is_abnormal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="lab_results")
    report = relationship("Report", back_populates="lab_results")
