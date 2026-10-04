"""SQLAlchemy Models for Prescription Intelligence and Medication Safety (Phase 5).

Provides schema for:
- Prescriptions (Prescription document headers & encounters)
- PrescriptionMedications (Extracted and normalized medication items)
- MedicationSafetyFindings (Auditable, evidence-backed safety alerts)
- MedicationInteractionRules (Extensible rule catalog for drug-drug interactions)
- MedicationContraindicationRules (Extensible rule catalog for contraindications)
- MedicationLabContextRules (Extensible rule catalog for lab-drug context signals)
- MedicationAllergyRules (Extensible rule catalog for drug-allergy mappings)
"""

import enum
import uuid
from datetime import datetime
from typing import List, Optional
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


class PrescriptionStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DISCONTINUED = "DISCONTINUED"
    EXTRACTED = "EXTRACTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEWED = "REVIEWED"


class MedicationReviewStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"


class SafetyFindingTypeEnum(str, enum.Enum):
    DRUG_DRUG_INTERACTION = "DRUG_DRUG_INTERACTION"
    POTENTIAL_ALLERGY_CONCERN = "POTENTIAL_ALLERGY_CONCERN"
    POTENTIAL_DUPLICATE = "POTENTIAL_DUPLICATE"
    INCOMPLETE_PRESCRIPTION = "INCOMPLETE_PRESCRIPTION"
    LAB_CONTEXT_SIGNAL = "LAB_CONTEXT_SIGNAL"
    CONTRAINDICATION_SIGNAL = "CONTRAINDICATION_SIGNAL"
    UNKNOWN_MEDICATION = "UNKNOWN_MEDICATION"
    UNKNOWN_DOSAGE = "UNKNOWN_DOSAGE"
    UNKNOWN_ROUTE = "UNKNOWN_ROUTE"
    UNKNOWN_FREQUENCY = "UNKNOWN_FREQUENCY"
    UNKNOWN_DURATION = "UNKNOWN_DURATION"


class SafetySeverityEnum(str, enum.Enum):
    INFO = "INFO"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Prescription(Base, TimestampMixin):
    """Represents a medical prescription encounter / document record."""
    __tablename__ = "prescriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("medical_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    report_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True)

    prescriber_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prescription_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    source_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=PrescriptionStatusEnum.ACTIVE.value, nullable=False, index=True)

    # Legacy Phase 0 support fields
    drug_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    generic_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    dosage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    frequency: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    route: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    prescribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="prescriptions")
    document = relationship("MedicalDocument", foreign_keys=[document_id])
    report = relationship("Report", back_populates="prescriptions")
    medications = relationship("PrescriptionMedication", back_populates="prescription", cascade="all, delete-orphan")
    safety_findings = relationship("MedicationSafetyFinding", back_populates="prescription", cascade="all, delete-orphan")


class PrescriptionMedication(Base, TimestampMixin):
    """Represents an extracted, normalized prescription medication entry."""
    __tablename__ = "prescription_medications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prescription_id: Mapped[str] = mapped_column(String(36), ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)

    raw_medication_name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_medication_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    generic_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    brand_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    strength_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    strength_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dosage_form: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    route: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    frequency_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    frequency_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dose_quantity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    duration_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    instruction_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_prn: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False, index=True)
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    bounding_box: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    review_status: Mapped[str] = mapped_column(String(50), default=MedicationReviewStatusEnum.PENDING.value, nullable=False, index=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    prescription = relationship("Prescription", back_populates="medications")
    patient = relationship("Patient", foreign_keys=[patient_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    safety_findings = relationship("MedicationSafetyFinding", back_populates="medication", cascade="all, delete-orphan")


class MedicationSafetyFinding(BaseModel if False else Base, TimestampMixin):
    """Represents an auditable medication safety alert (DDI, allergy, lab context, duplicate)."""
    __tablename__ = "medication_safety_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    prescription_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("prescriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    medication_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("prescription_medications.id", ondelete="SET NULL"), nullable=True, index=True)

    finding_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), default=SafetySeverityEnum.INFO.value, nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    clinical_association: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    rule_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    rule_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)

    requires_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    review_status: Mapped[str] = mapped_column(String(50), default=MedicationReviewStatusEnum.PENDING.value, nullable=False, index=True)
    clinician_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    patient = relationship("Patient", foreign_keys=[patient_id])
    prescription = relationship("Prescription", back_populates="safety_findings")
    medication = relationship("PrescriptionMedication", back_populates="safety_findings")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class MedicationInteractionRule(Base, TimestampMixin):
    """Database model for dynamic/persisted drug interaction rules."""
    __tablename__ = "medication_interaction_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    drug_a: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    drug_b: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    interaction_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default=SafetySeverityEnum.MODERATE.value, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    clinical_association: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    evidence_source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_version: Mapped[str] = mapped_column(String(50), default="2026.1", nullable=False)
    rule_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    requires_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
