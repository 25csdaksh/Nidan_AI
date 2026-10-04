import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class ImagingStudy(Base, TimestampMixin):
    __tablename__ = "imaging_studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    modality: Mapped[str] = mapped_column(String(50), nullable=False)  # X-RAY, ULTRASOUND, CT, MRI
    body_part: Mapped[str] = mapped_column(String(100), nullable=False)  # Chest, Abdomen, Pelvis, Right Knee
    view_position: Mapped[str] = mapped_column(String(50), nullable=True)  # PA, AP, Lateral
    dicom_series_uid: Mapped[str] = mapped_column(String(128), nullable=True)
    radiologist_impression: Mapped[str] = mapped_column(Text, nullable=True)
    structured_findings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    patient = relationship("Patient")
    report = relationship("Report", back_populates="imaging_studies")
