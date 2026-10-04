from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.patients.models import Patient
from app.modules.doctor_copilot.schemas import EvidenceItem, EvidenceType


async def build_patient_demographic_context(
    session: AsyncSession, patient_id: str
) -> Dict[str, Any]:
    """
    Retrieves patient demographics and structured allergy records.
    """
    stmt = select(Patient).where(Patient.id == patient_id)
    result = await session.execute(stmt)
    patient = result.scalar_one_or_none()

    if not patient:
        return {
            "patient_id": patient_id,
            "status": "NOT_FOUND",
            "demographics": {},
            "allergies": [],
            "evidence_items": [],
        }

    # Extract documented allergies if present in metadata/records
    allergies: List[str] = []
    if hasattr(patient, "known_allergies") and patient.known_allergies:
        allergies = list(patient.known_allergies)
    elif hasattr(patient, "allergies") and getattr(patient, "allergies"):
        allergies = list(getattr(patient, "allergies"))
    elif hasattr(patient, "emergency_contact") and isinstance(patient.emergency_contact, dict):
        allergies = patient.emergency_contact.get("documented_allergies", [])


    evidence_items: List[EvidenceItem] = []
    for idx, allergy in enumerate(allergies):
        evidence_items.append(
            EvidenceItem(
                evidence_id=f"EVID-ALLERGY-{idx+1}",
                type=EvidenceType.ALLERGY_RECORD,
                patient_id=patient_id,
                title="Documented Patient Allergy",
                value=str(allergy),
                status="DOCUMENTED",
                details={"allergen": str(allergy)},
            )
        )

    return {
        "patient_id": patient.id,
        "mrn": patient.mrn,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else "UNKNOWN",
        "gender": patient.gender or "UNKNOWN",
        "blood_group": patient.blood_group or "UNKNOWN",
        "allergies": allergies,
        "evidence_items": evidence_items,
    }
