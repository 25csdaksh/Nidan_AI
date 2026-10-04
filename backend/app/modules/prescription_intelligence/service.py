"""Prescription Intelligence & Medication Safety Service Layer (Phase 5).

Handles:
- Document OCR routing and prescription extraction
- Medication normalization & structured entity storage
- Multi-prescription longitudinal medication timeline
- Comprehensive safety analysis (DDIs, duplicates, allergy safety, lab context, contraindications)
- Clinician review workflows with HIPAA audit logging
- Strict RBAC & patient isolation
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppException, ForbiddenError, ResourceNotFoundError
from app.core.logging import logger
from app.core.security import CLINICAL_STAFF_ROLES, UserRole
from app.core.storage import get_storage_service
from app.modules.audit.schemas import AuditLogCreate
from app.modules.audit.service import AuditService
from app.modules.clinical_intelligence.models import ClinicalObservation
from app.modules.medical_documents.extraction.pipeline import MedicalExtractionPipeline
from app.modules.medical_documents.models import DocumentTypeEnum, MedicalDocument
from app.modules.patients.models import Patient
from app.modules.prescription_intelligence.extraction.prescription_extractor import PrescriptionExtractor
from app.modules.prescription_intelligence.models import (
    MedicationInteractionRule,
    MedicationReviewStatusEnum,
    MedicationSafetyFinding,
    Prescription,
    PrescriptionMedication,
    PrescriptionStatusEnum,
    SafetySeverityEnum,
)
from app.modules.prescription_intelligence.safety.allergy_engine import AllergyEngine
from app.modules.prescription_intelligence.safety.contraindication_engine import ContraindicationEngine
from app.modules.prescription_intelligence.safety.duplicate_engine import DuplicateEngine, RawMedicationInput
from app.modules.prescription_intelligence.safety.interaction_engine import InteractionEngine
from app.modules.prescription_intelligence.safety.lab_context_engine import LabContextEngine, RawLabObservationInput
from app.modules.prescription_intelligence.safety.rules import (
    ALLERGY_RULES,
    CONTRAINDICATION_RULES,
    DRUG_INTERACTION_RULES,
    LAB_CONTEXT_RULES,
)
from app.modules.prescription_intelligence.schemas import (
    MedicationReviewRequest,
    MedicationSafetyAnalysisRequest,
)


class PrescriptionIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = get_storage_service()
        self.audit_service = AuditService(db)
        self.extraction_pipeline = MedicalExtractionPipeline()

    def check_patient_authorization(self, patient_id: str, current_user: dict):
        """Validates that the authenticated user is authorized to access the patient's records."""
        user_role = (current_user.get("role") or "").lower()
        user_id = current_user.get("sub")

        # Patients can only access their own linked patient record
        if user_role == UserRole.PATIENT.value.lower():
            linked_patient_id = current_user.get("patient_id") or user_id
            if linked_patient_id != patient_id:
                raise ForbiddenError("Access denied: You are only authorized to access your own medical records.")
            return

        # Clinical staff and admins are authorized
        allowed_roles = [r.value.lower() for r in CLINICAL_STAFF_ROLES]
        if user_role not in allowed_roles and user_role != UserRole.SUPER_ADMIN.value.lower():
            raise ForbiddenError("Access denied: Insufficient clinical permissions.")

    def require_clinician_role(self, current_user: dict, action_name: str = "perform clinical review"):
        """Ensures the caller has a licensed clinician or admin role."""
        user_role = (current_user.get("role") or "").lower()
        allowed_roles = [r.value.lower() for r in CLINICAL_STAFF_ROLES]
        if user_role not in allowed_roles and user_role != UserRole.SUPER_ADMIN.value.lower():
            raise ForbiddenError(f"Access denied: Only licensed clinicians can {action_name}.")

    async def extract_prescription_from_document(
        self,
        document_id: str,
        current_user: dict,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Prescription:
        """Extracts structured medications from a medical document and runs safety checks."""
        # 1. Load document
        stmt = select(MedicalDocument).where(MedicalDocument.id == document_id, MedicalDocument.is_deleted == False)
        result = await self.db.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise ResourceNotFoundError(f"Medical document '{document_id}' not found.")

        self.check_patient_authorization(doc.patient_id, current_user)

        # 2. Retrieve document bytes
        file_bytes = await self.storage.get_file_bytes(doc.storage_key)

        # 3. Perform OCR extraction
        pipeline_res = await self.extraction_pipeline.process(
            file_bytes=file_bytes,
            mime_type=doc.mime_type,
            has_embedded_text=(doc.mime_type == "application/pdf"),
        )

        # 4. Extract structured prescription and medications
        extracted_rx = PrescriptionExtractor.extract(pipeline_res.ocr_result)

        # 5. Check if prescription record already exists for this document
        rx_stmt = (
            select(Prescription)
            .where(Prescription.document_id == document_id)
            .options(
                selectinload(Prescription.medications),
                selectinload(Prescription.safety_findings),
            )
        )
        existing_rx = (await self.db.execute(rx_stmt)).scalar_one_or_none()

        if existing_rx:
            # Update existing prescription header
            existing_rx.prescriber_name = extracted_rx.prescriber_name or existing_rx.prescriber_name
            existing_rx.prescription_date = extracted_rx.prescription_date or existing_rx.prescription_date
            existing_rx.source_confidence = extracted_rx.source_confidence
            existing_rx.status = extracted_rx.status
            prescription = existing_rx
        else:
            prescription = Prescription(
                id=str(uuid.uuid4()),
                patient_id=doc.patient_id,
                document_id=doc.id,
                prescriber_name=extracted_rx.prescriber_name,
                prescription_date=extracted_rx.prescription_date,
                source_confidence=extracted_rx.source_confidence,
                status=extracted_rx.status,
            )
            self.db.add(prescription)
            await self.db.flush()

        # 6. Delete old medications for idempotency if updating
        if existing_rx:
            for old_med in list(existing_rx.medications):
                await self.db.delete(old_med)
            await self.db.flush()

        # 7. Insert extracted medications
        created_meds: List[PrescriptionMedication] = []
        for med_item in extracted_rx.medications:
            med_model = PrescriptionMedication(
                id=str(uuid.uuid4()),
                prescription_id=prescription.id,
                patient_id=doc.patient_id,
                raw_medication_name=med_item.raw_medication_name,
                canonical_medication_name=med_item.canonical_medication_name,
                generic_name=med_item.generic_name,
                brand_name=med_item.brand_name,
                strength_value=med_item.strength_value,
                strength_unit=med_item.strength_unit,
                dosage_form=med_item.dosage_form,
                route=med_item.route,
                frequency_code=med_item.frequency_code,
                frequency_text=med_item.frequency_text,
                dose_quantity=med_item.dose_quantity,
                duration_value=med_item.duration_value,
                duration_unit=med_item.duration_unit,
                instruction_text=med_item.instruction_text,
                is_prn=med_item.is_prn,
                confidence=med_item.confidence,
                source_text=med_item.source_text,
                page_number=med_item.page_number,
                bounding_box=med_item.bounding_box,
                review_status=MedicationReviewStatusEnum.PENDING.value,
            )
            self.db.add(med_model)
            created_meds.append(med_model)

        await self.db.flush()

        # 8. Run automatic safety analysis on the patient's medications
        await self.run_medication_safety_analysis(
            patient_id=doc.patient_id,
            request_data=MedicationSafetyAnalysisRequest(),
            current_user=current_user,
            client_ip=client_ip,
            target_prescription_id=prescription.id,
        )

        # 9. Audit event
        actor_id = current_user.get("sub")
        await self.audit_service.log_event(
            AuditLogCreate(
                actor_id=actor_id,
                action="PRESCRIPTION_EXTRACTED",
                resource_type="PRESCRIPTION",
                resource_id=prescription.id,
                ip_address=client_ip,
                user_agent=user_agent,
                details={
                    "document_id": document_id,
                    "medications_count": len(created_meds),
                    "prescriber": prescription.prescriber_name,
                    "status": prescription.status,
                },
            )
        )

        await self.db.commit()
        return await self.get_prescription(prescription.id, current_user)

    async def get_prescription(self, prescription_id: str, current_user: dict) -> Prescription:
        """Retrieves a prescription with its medications and safety findings."""
        stmt = (
            select(Prescription)
            .where(Prescription.id == prescription_id)
            .options(
                selectinload(Prescription.medications),
                selectinload(Prescription.safety_findings),
            )
        )
        result = await self.db.execute(stmt)
        rx = result.scalar_one_or_none()
        if not rx:
            raise ResourceNotFoundError(f"Prescription '{prescription_id}' not found.")

        self.check_patient_authorization(rx.patient_id, current_user)
        return rx

    async def get_prescription_by_document(self, document_id: str, current_user: dict) -> Optional[Prescription]:
        """Retrieves prescription associated with a medical document."""
        stmt = (
            select(Prescription)
            .where(Prescription.document_id == document_id)
            .options(
                selectinload(Prescription.medications),
                selectinload(Prescription.safety_findings),
            )
        )
        result = await self.db.execute(stmt)
        rx = result.scalar_one_or_none()
        if rx:
            self.check_patient_authorization(rx.patient_id, current_user)
        return rx

    async def get_patient_prescriptions(
        self,
        patient_id: str,
        current_user: dict,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
    ) -> Tuple[List[Prescription], int]:
        """Returns paginated prescriptions for a patient."""
        self.check_patient_authorization(patient_id, current_user)

        stmt = select(Prescription).where(Prescription.patient_id == patient_id)
        if status and status.upper() != "ALL":
            stmt = stmt.where(Prescription.status == status.upper())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            stmt.options(
                selectinload(Prescription.medications),
                selectinload(Prescription.safety_findings),
            )
            .order_by(Prescription.prescription_date.desc().nullslast(), Prescription.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_patient_medications(
        self,
        patient_id: str,
        current_user: dict,
        only_active: bool = False,
        canonical_name: Optional[str] = None,
    ) -> List[PrescriptionMedication]:
        """Returns all extracted medications for a patient."""
        self.check_patient_authorization(patient_id, current_user)

        stmt = select(PrescriptionMedication).where(PrescriptionMedication.patient_id == patient_id)
        if canonical_name:
            stmt = stmt.where(PrescriptionMedication.canonical_medication_name.ilike(f"%{canonical_name}%"))

        stmt = stmt.order_by(PrescriptionMedication.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_patient_medication_timeline(self, patient_id: str, current_user: dict) -> Dict[str, Any]:
        """Assembles a longitudinal timeline of prescriptions and documented medications."""
        self.check_patient_authorization(patient_id, current_user)

        prescriptions, total = await self.get_patient_prescriptions(patient_id, current_user, page=1, page_size=200)

        events = []
        active_meds_set = set()
        total_meds_count = 0

        for rx in prescriptions:
            med_count = len(rx.medications)
            total_meds_count += med_count
            for m in rx.medications:
                if m.canonical_medication_name and m.canonical_medication_name != "UNKNOWN":
                    active_meds_set.add(m.canonical_medication_name)

            events.append({
                "prescription_id": rx.id,
                "document_id": rx.document_id,
                "prescriber_name": rx.prescriber_name,
                "prescription_date": rx.prescription_date,
                "medications": rx.medications,
                "safety_alert_count": len(rx.safety_findings),
            })

        return {
            "patient_id": patient_id,
            "total_prescriptions": len(prescriptions),
            "total_medications": total_meds_count,
            "events": events,
            "active_medications_summary": sorted(list(active_meds_set)),
        }

    async def run_medication_safety_analysis(
        self,
        patient_id: str,
        request_data: MedicationSafetyAnalysisRequest,
        current_user: dict,
        client_ip: Optional[str] = None,
        target_prescription_id: Optional[str] = None,
    ) -> List[MedicationSafetyFinding]:
        """Executes multi-rule medication safety analysis across patient prescriptions."""
        self.check_patient_authorization(patient_id, current_user)

        # 1. Load patient metadata
        p_stmt = select(Patient).where(Patient.id == patient_id)
        patient = (await self.db.execute(p_stmt)).scalar_one_or_none()
        if not patient:
            raise ResourceNotFoundError(f"Patient '{patient_id}' not found.")

        # 2. Load patient medications
        med_stmt = select(PrescriptionMedication).where(PrescriptionMedication.patient_id == patient_id)
        if target_prescription_id:
            med_stmt = med_stmt.where(PrescriptionMedication.prescription_id == target_prescription_id)
        med_results = (await self.db.execute(med_stmt)).scalars().all()

        raw_med_inputs = [
            RawMedicationInput(
                id=m.id,
                prescription_id=m.prescription_id,
                document_id=None,
                raw_medication_name=m.raw_medication_name,
                canonical_medication_name=m.canonical_medication_name,
                generic_name=m.generic_name,
                strength_value=m.strength_value,
                strength_unit=m.strength_unit,
                source_text=m.source_text,
                page_number=m.page_number,
            )
            for m in med_results
        ]

        generated_findings: List[MedicationSafetyFinding] = []

        # 3. Drug-Drug Interactions
        if request_data.include_ddi and len(raw_med_inputs) >= 2:
            ddi_findings = InteractionEngine.evaluate(raw_med_inputs)
            for f in ddi_findings:
                finding_model = MedicationSafetyFinding(
                    id=str(uuid.uuid4()),
                    patient_id=patient_id,
                    prescription_id=f.evidence.get("prescription_id"),
                    medication_id=f.evidence.get("medication_id"),
                    finding_type=f.finding_type,
                    severity=f.severity,
                    title=f.title,
                    description=f.description,
                    clinical_association=f.clinical_association,
                    evidence=f.evidence,
                    confidence=f.confidence,
                    rule_id=f.rule_id,
                    rule_version=f.rule_version,
                    requires_review=f.requires_review,
                    review_status=MedicationReviewStatusEnum.PENDING.value,
                )
                self.db.add(finding_model)
                generated_findings.append(finding_model)

        # 4. Duplicate Medication Detection
        if request_data.include_duplicates and len(raw_med_inputs) >= 2:
            dup_findings = DuplicateEngine.evaluate(raw_med_inputs)
            for f in dup_findings:
                finding_model = MedicationSafetyFinding(
                    id=str(uuid.uuid4()),
                    patient_id=patient_id,
                    prescription_id=f.evidence.get("prescription_id"),
                    medication_id=f.evidence.get("medication_id"),
                    finding_type=f.finding_type,
                    severity=f.severity,
                    title=f.title,
                    description=f.description,
                    clinical_association=f.clinical_association,
                    evidence=f.evidence,
                    confidence=f.confidence,
                    rule_id=f.rule_id,
                    rule_version=f.rule_version,
                    requires_review=f.requires_review,
                    review_status=MedicationReviewStatusEnum.PENDING.value,
                )
                self.db.add(finding_model)
                generated_findings.append(finding_model)

        # 5. Allergy Safety Evaluation
        if request_data.include_allergies and patient.known_allergies:
            allergy_findings = AllergyEngine.evaluate(raw_med_inputs, patient.known_allergies)
            for f in allergy_findings:
                finding_model = MedicationSafetyFinding(
                    id=str(uuid.uuid4()),
                    patient_id=patient_id,
                    prescription_id=f.evidence.get("prescription_id"),
                    medication_id=f.evidence.get("medication_id"),
                    finding_type=f.finding_type,
                    severity=f.severity,
                    title=f.title,
                    description=f.description,
                    clinical_association=f.clinical_association,
                    evidence=f.evidence,
                    confidence=f.confidence,
                    rule_id=f.rule_id,
                    rule_version=f.rule_version,
                    requires_review=f.requires_review,
                    review_status=MedicationReviewStatusEnum.PENDING.value,
                )
                self.db.add(finding_model)
                generated_findings.append(finding_model)

        # 6. Lab-Medication Context Signals
        if request_data.include_lab_context:
            # Load patient's clinical observations
            obs_stmt = select(ClinicalObservation).where(ClinicalObservation.patient_id == patient_id)
            obs_results = (await self.db.execute(obs_stmt)).scalars().all()
            if obs_results:
                raw_obs_inputs = [
                    RawLabObservationInput(
                        id=o.id,
                        document_id=o.document_id,
                        analyte=o.analyte,
                        canonical_name=o.canonical_name,
                        value=o.value,
                        normalized_value=o.normalized_value,
                        unit=o.unit,
                        technical_status=o.technical_status,
                        observation_date=str(o.observation_date) if o.observation_date else None,
                    )
                    for o in obs_results
                ]
                lab_findings = LabContextEngine.evaluate(raw_med_inputs, raw_obs_inputs)
                for f in lab_findings:
                    finding_model = MedicationSafetyFinding(
                        id=str(uuid.uuid4()),
                        patient_id=patient_id,
                        prescription_id=f.evidence.get("prescription_id"),
                        medication_id=f.evidence.get("medication_id"),
                        finding_type=f.finding_type,
                        severity=f.severity,
                        title=f.title,
                        description=f.description,
                        clinical_association=f.clinical_association,
                        evidence=f.evidence,
                        confidence=f.confidence,
                        rule_id=f.rule_id,
                        rule_version=f.rule_version,
                        requires_review=f.requires_review,
                        review_status=MedicationReviewStatusEnum.PENDING.value,
                    )
                    self.db.add(finding_model)
                    generated_findings.append(finding_model)

        # 7. Contraindications with chronic conditions
        if request_data.include_contraindications and patient.chronic_conditions:
            ci_findings = ContraindicationEngine.evaluate(raw_med_inputs, patient.chronic_conditions)
            for f in ci_findings:
                finding_model = MedicationSafetyFinding(
                    id=str(uuid.uuid4()),
                    patient_id=patient_id,
                    prescription_id=f.evidence.get("prescription_id"),
                    medication_id=f.evidence.get("medication_id"),
                    finding_type=f.finding_type,
                    severity=f.severity,
                    title=f.title,
                    description=f.description,
                    clinical_association=f.clinical_association,
                    evidence=f.evidence,
                    confidence=f.confidence,
                    rule_id=f.rule_id,
                    rule_version=f.rule_version,
                    requires_review=f.requires_review,
                    review_status=MedicationReviewStatusEnum.PENDING.value,
                )
                self.db.add(finding_model)
                generated_findings.append(finding_model)

        await self.db.flush()

        # 8. Audit event
        actor_id = current_user.get("sub")
        await self.audit_service.log_event(
            AuditLogCreate(
                actor_id=actor_id,
                action="MEDICATION_SAFETY_ANALYSIS_COMPLETED",
                resource_type="PATIENT",
                resource_id=patient_id,
                ip_address=client_ip,
                details={
                    "medications_analyzed": len(raw_med_inputs),
                    "findings_generated": len(generated_findings),
                },
            )
        )

        return generated_findings

    async def get_medication_safety_findings(
        self,
        patient_id: str,
        current_user: dict,
        severity: Optional[str] = None,
        finding_type: Optional[str] = None,
        review_status: Optional[str] = None,
    ) -> List[MedicationSafetyFinding]:
        """Returns filtered safety findings for a patient."""
        self.check_patient_authorization(patient_id, current_user)

        stmt = select(MedicationSafetyFinding).where(MedicationSafetyFinding.patient_id == patient_id)
        if severity and severity.upper() != "ALL":
            stmt = stmt.where(MedicationSafetyFinding.severity == severity.upper())
        if finding_type and finding_type.upper() != "ALL":
            stmt = stmt.where(MedicationSafetyFinding.finding_type == finding_type.upper())
        if review_status and review_status.upper() != "ALL":
            stmt = stmt.where(MedicationSafetyFinding.review_status == review_status.upper())

        stmt = stmt.order_by(MedicationSafetyFinding.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_medication_safety_finding(
        self,
        patient_id: str,
        finding_id: str,
        current_user: dict,
    ) -> MedicationSafetyFinding:
        """Retrieves a single safety finding by ID."""
        self.check_patient_authorization(patient_id, current_user)

        stmt = select(MedicationSafetyFinding).where(
            MedicationSafetyFinding.id == finding_id,
            MedicationSafetyFinding.patient_id == patient_id,
        )
        result = await self.db.execute(stmt)
        finding = result.scalar_one_or_none()
        if not finding:
            raise ResourceNotFoundError(f"Medication safety finding '{finding_id}' not found.")
        return finding

    async def review_medication_safety_finding(
        self,
        finding_id: str,
        review_data: MedicationReviewRequest,
        current_user: dict,
        client_ip: Optional[str] = None,
    ) -> MedicationSafetyFinding:
        """Allows a licensed clinician to review, verify, or reject a safety alert."""
        self.require_clinician_role(current_user, action_name="review medication safety alerts")

        stmt = select(MedicationSafetyFinding).where(MedicationSafetyFinding.id == finding_id)
        finding = (await self.db.execute(stmt)).scalar_one_or_none()
        if not finding:
            raise ResourceNotFoundError(f"Safety finding '{finding_id}' not found.")

        # Update review fields
        valid_statuses = [s.value for s in MedicationReviewStatusEnum]
        if review_data.review_status.upper() not in valid_statuses:
            raise AppException(f"Invalid review status: '{review_data.review_status}'. Must be one of {valid_statuses}")

        actor_id = current_user.get("sub")
        finding.review_status = review_data.review_status.upper()
        finding.clinician_note = review_data.clinician_note
        finding.reviewed_by = actor_id
        finding.reviewed_at = datetime.now(timezone.utc)

        await self.audit_service.log_event(
            AuditLogCreate(
                actor_id=actor_id,
                action="MEDICATION_SAFETY_FINDING_REVIEWED",
                resource_type="MEDICATION_SAFETY_FINDING",
                resource_id=finding_id,
                ip_address=client_ip,
                details={
                    "patient_id": finding.patient_id,
                    "review_status": finding.review_status,
                    "clinician_note": finding.clinician_note,
                },
            )
        )

        await self.db.commit()
        await self.db.refresh(finding)
        return finding

    @classmethod
    def get_all_rules(cls) -> List[Dict[str, Any]]:
        """Returns all configured safety rules across DDIs, allergies, lab context, and contraindications."""
        all_rules = []
        for r in DRUG_INTERACTION_RULES:
            all_rules.append({
                "rule_id": r.rule_id,
                "rule_type": "DDI",
                "drug_a": r.drug_a,
                "drug_b": r.drug_b,
                "severity": r.severity,
                "title": r.title,
                "description": r.description,
                "clinical_association": r.clinical_association,
                "evidence_source": r.evidence_source,
                "rule_version": r.rule_version,
                "active": r.active,
            })
        for a in ALLERGY_RULES:
            all_rules.append({
                "rule_id": a.rule_id,
                "rule_type": "ALLERGY",
                "medication": a.medication,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "clinical_association": f"Documented {a.allergen_class} allergy",
                "evidence_source": a.evidence_source,
                "rule_version": a.rule_version,
                "active": True,
            })
        for l in LAB_CONTEXT_RULES:
            all_rules.append({
                "rule_id": l.rule_id,
                "rule_type": "LAB_CONTEXT",
                "medication": l.medication,
                "severity": l.severity,
                "title": l.title,
                "description": l.description,
                "clinical_association": l.clinical_association,
                "evidence_source": l.evidence_source,
                "rule_version": l.rule_version,
                "active": True,
            })
        for c in CONTRAINDICATION_RULES:
            all_rules.append({
                "rule_id": c.rule_id,
                "rule_type": "CONTRAINDICATION",
                "medication": c.medication,
                "severity": c.severity,
                "title": c.title,
                "description": c.description,
                "clinical_association": f"Documented history of {c.condition}",
                "evidence_source": c.evidence_source,
                "rule_version": c.rule_version,
                "active": True,
            })
        return all_rules
