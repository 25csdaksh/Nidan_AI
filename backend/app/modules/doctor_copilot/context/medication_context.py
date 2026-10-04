from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.modules.prescription_intelligence.models import (
    PrescriptionMedication,
    MedicationSafetyFinding,
)
from app.modules.doctor_copilot.schemas import EvidenceItem, EvidenceType


async def build_medication_context(
    session: AsyncSession,
    patient_id: str,
    limit_medications: int = 50,
    limit_findings: int = 50,
) -> Dict[str, Any]:
    """
    Retrieves extracted medications and active medication safety findings.
    """
    # 1. Fetch prescription medications
    med_stmt = (
        select(PrescriptionMedication)
        .where(PrescriptionMedication.patient_id == patient_id)
        .order_by(desc(PrescriptionMedication.created_at))
        .limit(limit_medications)
    )
    med_res = await session.execute(med_stmt)
    medications = med_res.scalars().all()

    # 2. Fetch medication safety findings
    saf_stmt = (
        select(MedicationSafetyFinding)
        .where(MedicationSafetyFinding.patient_id == patient_id)
        .order_by(desc(MedicationSafetyFinding.created_at))
        .limit(limit_findings)
    )
    saf_res = await session.execute(saf_stmt)
    safety_findings = saf_res.scalars().all()

    evidence_items: List[EvidenceItem] = []
    formatted_medications: List[Dict[str, Any]] = []
    formatted_safety: List[Dict[str, Any]] = []

    for idx, med in enumerate(medications):
        ev_id = f"EVID-MED-{idx+1}"
        strength_str = f"{med.strength_value} {med.strength_unit}" if med.strength_value and med.strength_unit else None
        
        evidence_items.append(
            EvidenceItem(
                evidence_id=ev_id,
                type=EvidenceType.MEDICATION,
                patient_id=patient_id,
                prescription_id=med.prescription_id,
                medication_id=med.id,
                title=f"Medication: {med.canonical_medication_name or med.raw_medication_name}",
                value=strength_str,
                status=med.review_status,
                confidence=med.confidence,
                review_status=med.review_status,
                source_text=med.source_text,
                details={
                    "raw_name": med.raw_medication_name,
                    "canonical_name": med.canonical_medication_name,
                    "generic_name": med.generic_name,
                    "strength": strength_str,
                    "dosage_form": med.dosage_form,
                    "route": med.route,
                    "frequency": med.frequency_text or med.frequency_code,
                    "duration": f"{med.duration_value} {med.duration_unit}" if med.duration_value else None,
                    "is_prn": med.is_prn,
                    "instructions": med.instruction_text,
                }
            )
        )
        formatted_medications.append({
            "evidence_id": ev_id,
            "id": med.id,
            "prescription_id": med.prescription_id,
            "raw_name": med.raw_medication_name,
            "canonical_name": med.canonical_medication_name,
            "generic_name": med.generic_name,
            "strength": strength_str,
            "dosage_form": med.dosage_form,
            "route": med.route,
            "frequency": med.frequency_text or med.frequency_code,
            "duration": f"{med.duration_value} {med.duration_unit}" if med.duration_value else None,
            "is_prn": med.is_prn,
            "instructions": med.instruction_text,
            "confidence": med.confidence,
            "review_status": med.review_status,
        })

    for idx, saf in enumerate(safety_findings):
        ev_id = f"EVID-SAFETY-{idx+1}"
        evidence_items.append(
            EvidenceItem(
                evidence_id=ev_id,
                type=EvidenceType.MEDICATION_SAFETY,
                patient_id=patient_id,
                prescription_id=saf.prescription_id,
                medication_id=saf.medication_id,
                rule_id=saf.rule_id,
                title=saf.title,
                severity=saf.severity,
                status=saf.finding_type,
                confidence=saf.confidence,
                review_status=saf.review_status,
                details={
                    "finding_type": saf.finding_type,
                    "description": saf.description,
                    "clinical_association": saf.clinical_association,
                    "rule_version": saf.rule_version,
                    "requires_review": saf.requires_review,
                    "clinician_note": saf.clinician_note,
                }
            )
        )
        formatted_safety.append({
            "evidence_id": ev_id,
            "id": saf.id,
            "finding_type": saf.finding_type,
            "severity": saf.severity,
            "title": saf.title,
            "description": saf.description,
            "clinical_association": saf.clinical_association,
            "rule_id": saf.rule_id,
            "requires_review": saf.requires_review,
            "review_status": saf.review_status,
            "clinician_note": saf.clinician_note,
        })

    return {
        "medications_count": len(formatted_medications),
        "safety_findings_count": len(formatted_safety),
        "medications": formatted_medications,
        "safety_findings": formatted_safety,
        "evidence_items": evidence_items,
    }
