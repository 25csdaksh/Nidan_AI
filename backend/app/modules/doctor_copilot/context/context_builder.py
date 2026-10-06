import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.modules.doctor_copilot.schemas import EvidenceItem, EvidenceType
from app.modules.doctor_copilot.context.patient_context import build_patient_demographic_context
from app.modules.doctor_copilot.context.laboratory_context import build_laboratory_context
from app.modules.doctor_copilot.context.longitudinal_context import build_longitudinal_context
from app.modules.doctor_copilot.context.medication_context import build_medication_context
from app.modules.doctor_copilot.context.prescription_context import build_prescription_context
from app.modules.doctor_copilot.context.document_context import build_document_context
from app.modules.doctor_copilot.context.clinician_note_context import build_clinician_note_context
from app.modules.doctor_copilot.context.imaging_context import build_imaging_context

logger = logging.getLogger("nidan_ai.doctor_copilot.context_builder")


class ClinicalContextBuilder:
    """
    Constructs a structured, verified, bounded patient context for the Doctor Copilot.
    Separates verified/reviewed data from unverified/unknown data.
    """

    def __init__(
        self,
        max_documents: int = settings.COPILOT_MAX_DOCUMENTS,
        max_observations: int = settings.COPILOT_MAX_OBSERVATIONS,
        max_findings: int = settings.COPILOT_MAX_FINDINGS,
        max_medications: int = settings.COPILOT_MAX_MEDICATIONS,
        max_notes: int = settings.COPILOT_MAX_NOTES,
    ):
        self.max_documents = max_documents
        self.max_observations = max_observations
        self.max_findings = max_findings
        self.max_medications = max_medications
        self.max_notes = max_notes

    async def build(
        self, session: AsyncSession, patient_id: str
    ) -> Dict[str, Any]:
        """
        Gathers all domain contexts into a consolidated bounded payload.
        """
        # 1. Patient Demographics & Allergies
        patient_data = await build_patient_demographic_context(session, patient_id)

        # 2. Lab Observations & Findings
        lab_data = await build_laboratory_context(
            session, patient_id, self.max_observations, self.max_findings
        )

        # 3. Longitudinal Trends
        long_data = await build_longitudinal_context(session, patient_id)

        # 4. Medication & Safety
        med_data = await build_medication_context(
            session, patient_id, self.max_medications, self.max_findings
        )

        # 5. Prescriptions
        rx_data = await build_prescription_context(session, patient_id, self.max_documents)

        # 6. Documents
        doc_data = await build_document_context(session, patient_id, self.max_documents)

        # 7. Clinician Notes
        note_data = await build_clinician_note_context(session, patient_id, self.max_notes)

        # 8. Imaging Studies & Findings (Phase 7)
        imaging_data = await build_imaging_context(session, patient_id, max_studies=5, max_findings=self.max_findings)

        # Aggregate evidence items
        all_evidence: List[EvidenceItem] = []
        all_evidence.extend(patient_data.get("evidence_items", []))
        all_evidence.extend(lab_data.get("evidence_items", []))
        all_evidence.extend(long_data.get("evidence_items", []))
        all_evidence.extend(med_data.get("evidence_items", []))
        all_evidence.extend(rx_data.get("evidence_items", []))
        all_evidence.extend(doc_data.get("evidence_items", []))
        all_evidence.extend(note_data.get("evidence_items", []))
        all_evidence.extend(imaging_data.get("evidence_items", []))

        # Evidence dictionary keyed by evidence_id
        evidence_catalog: Dict[str, EvidenceItem] = {
            ev.evidence_id: ev for ev in all_evidence
        }

        # Calculate statistics
        records_considered = (
            lab_data.get("observations_count", 0)
            + lab_data.get("findings_count", 0)
            + med_data.get("medications_count", 0)
            + med_data.get("safety_findings_count", 0)
            + rx_data.get("prescriptions_count", 0)
            + doc_data.get("documents_count", 0)
            + note_data.get("notes_count", 0)
            + imaging_data.get("studies_count", 0)
        )
        records_included = len(all_evidence)
        records_excluded = max(0, records_considered - records_included)

        # Assess Data Quality & Missing Information
        data_quality_notes: List[str] = []
        if not patient_data.get("allergies"):
            data_quality_notes.append("No documented allergies recorded in the patient profile.")
        if lab_data.get("observations_count", 0) == 0:
            data_quality_notes.append("No laboratory observations available in the current record.")
        if med_data.get("medications_count", 0) == 0:
            data_quality_notes.append("No prescription medications documented in the available record.")
        if not long_data.get("analysis_available", False):
            data_quality_notes.append("Longitudinal multi-visit analysis has not been executed or insufficient encounters exist.")
        if doc_data.get("documents_count", 0) == 0:
            data_quality_notes.append("No uploaded medical documents found for this patient.")
        if not imaging_data.get("has_imaging", False):
            data_quality_notes.append("No chest X-ray or medical imaging studies recorded for this patient.")

        return {
            "patient": patient_data,
            "laboratory": lab_data,
            "longitudinal": long_data,
            "medications": med_data,
            "prescriptions": rx_data,
            "documents": doc_data,
            "clinician_notes": note_data,
            "imaging": imaging_data,
            "evidence_catalog": evidence_catalog,
            "all_evidence": all_evidence,
            "data_quality_notes": data_quality_notes,
            "meta": {
                "records_considered": records_considered,
                "records_included": records_included,
                "records_excluded": records_excluded,
                "context_version": "1.0",
            },
        }
