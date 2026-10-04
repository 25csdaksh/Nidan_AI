import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class AIAnalysisJob(Base, TimestampMixin):
    __tablename__ = "ai_analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="QUEUED", nullable=False)  # QUEUED, PROCESSING, COMPLETED, FAILED, PHASE_0_READY
    pipeline_version: Mapped[str] = mapped_column(String(50), default="phase0-scaffold", nullable=False)
    insights_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    doctor_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    doctor_notes: Mapped[str] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    report = relationship("Report", back_populates="ai_jobs")
    verified_by = relationship("User")
