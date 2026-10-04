import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class Prescription(Base, TimestampMixin):
    __tablename__ = "prescriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True)
    drug_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    generic_name: Mapped[str] = mapped_column(String(200), nullable=True)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., 500mg
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., Twice daily after meals
    route: Mapped[str] = mapped_column(String(50), default="ORAL", nullable=False)  # ORAL, IV, TOPICAL
    duration_days: Mapped[int] = mapped_column(Integer, nullable=True)
    instructions: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    prescribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="prescriptions")
    report = relationship("Report", back_populates="prescriptions")
