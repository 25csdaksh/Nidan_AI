import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class CopilotSession(Base):
    """
    Doctor Copilot conversation session scoped to a specific patient.
    Enforces patient isolation and clinician RBAC.
    """
    __tablename__ = "copilot_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clinician_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Clinical Case Review"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ACTIVE", index=True
    )  # ACTIVE, ARCHIVED, CLOSED
    context_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="1.0"
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    messages: Mapped[List["CopilotMessage"]] = relationship(
        "CopilotMessage", back_populates="session", cascade="all, delete-orphan", order_by="CopilotMessage.created_at"
    )

    __table_args__ = (
        Index("ix_copilot_sessions_patient_created", "patient_id", "created_at"),
        Index("ix_copilot_sessions_clinician_patient", "clinician_id", "patient_id"),
    )


class CopilotMessage(Base):
    """
    Immutable individual message in a Copilot conversation session.
    Stores query, structured LLM response, evidence citations, safety audit, and model versions.
    """
    __tablename__ = "copilot_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("copilot_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # user, assistant, system
    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    query_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="GENERAL_QUERY", index=True
    )
    structured_response: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    evidence_ids: Mapped[List[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    safety_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PASSED", index=True
    )  # PASSED, BLOCKED, FLAGGED, PROHIBITED_REQUEST
    model_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="nidan-deterministic"
    )
    model_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="1.0"
    )
    prompt_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="1.0"
    )
    safety_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="1.0"
    )
    response_latency_ms: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    session: Mapped["CopilotSession"] = relationship(
        "CopilotSession", back_populates="messages"
    )
    feedback: Mapped[List["CopilotFeedback"]] = relationship(
        "CopilotFeedback", back_populates="message", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_copilot_messages_session_created", "session_id", "created_at"),
        Index("ix_copilot_messages_patient_created", "patient_id", "created_at"),
    )


class CopilotFeedback(Base):
    """
    Clinician feedback on a Copilot generated answer.
    """
    __tablename__ = "copilot_feedback"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    message_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("copilot_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clinician_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # HELPFUL, NOT_HELPFUL
    feedback_category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # HELPFUL, NOT_HELPFUL, EVIDENCE_INCORRECT, MISSING_EVIDENCE, UNSAFE_WORDING, OTHER
    comments: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    message: Mapped["CopilotMessage"] = relationship(
        "CopilotMessage", back_populates="feedback"
    )

