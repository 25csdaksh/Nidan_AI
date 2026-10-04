from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.modules.prescription_intelligence.models import Prescription
from app.modules.doctor_copilot.schemas import EvidenceItem, EvidenceType


async def build_prescription_context(
    session: AsyncSession,
    patient_id: str,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Retrieves prescription documents and prescriber metadata.
    """
    stmt = (
        select(Prescription)
        .where(Prescription.patient_id == patient_id)
        .order_by(desc(Prescription.prescription_date), desc(Prescription.created_at))
        .limit(limit)
    )
    res = await session.execute(stmt)
    prescriptions = res.scalars().all()

    evidence_items: List[EvidenceItem] = []
    formatted: List[Dict[str, Any]] = []

    for idx, rx in enumerate(prescriptions):
        ev_id = f"EVID-RX-{idx+1}"
        date_str = rx.prescription_date.strftime("%Y-%m-%d") if rx.prescription_date else "UNKNOWN"
        evidence_items.append(
            EvidenceItem(
                evidence_id=ev_id,
                type=EvidenceType.PRESCRIPTION,
                patient_id=patient_id,
                document_id=rx.document_id,
                prescription_id=rx.id,
                date=date_str,
                title=f"Prescription ({date_str})",
                value=rx.prescriber_name or "Prescriber Unspecified",
                status=rx.status,
                confidence=rx.source_confidence,
                details={
                    "prescriber_name": rx.prescriber_name,
                    "status": rx.status,
                }
            )
        )
        formatted.append({
            "evidence_id": ev_id,
            "id": rx.id,
            "document_id": rx.document_id,
            "prescriber_name": rx.prescriber_name,
            "prescription_date": date_str,
            "status": rx.status,
            "source_confidence": rx.source_confidence,
        })

    return {
        "prescriptions_count": len(formatted),
        "prescriptions": formatted,
        "evidence_items": evidence_items,
    }
