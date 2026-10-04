from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.modules.clinical_intelligence.models import LongitudinalReviewNote
from app.modules.doctor_copilot.schemas import EvidenceItem, EvidenceType


async def build_clinician_note_context(
    session: AsyncSession,
    patient_id: str,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Retrieves clinician longitudinal review notes.
    """
    stmt = (
        select(LongitudinalReviewNote)
        .where(LongitudinalReviewNote.patient_id == patient_id)
        .order_by(desc(LongitudinalReviewNote.created_at))
        .limit(limit)
    )
    res = await session.execute(stmt)
    notes = res.scalars().all()

    evidence_items: List[EvidenceItem] = []
    formatted: List[Dict[str, Any]] = []

    for idx, note in enumerate(notes):
        ev_id = f"EVID-NOTE-{idx+1}"
        date_str = note.created_at.strftime("%Y-%m-%d %H:%M") if note.created_at else "UNKNOWN"
        evidence_items.append(
            EvidenceItem(
                evidence_id=ev_id,
                type=EvidenceType.CLINICIAN_NOTE,
                patient_id=patient_id,
                date=date_str,
                title=f"Clinician Note ({date_str})",
                value=note.note[:100] + ("..." if len(note.note) > 100 else ""),
                status="REVIEW_NOTE",
                details={
                    "author_id": note.author_id,
                    "analysis_id": note.analysis_id,
                    "full_note": note.note,
                }
            )
        )
        formatted.append({
            "evidence_id": ev_id,
            "id": note.id,
            "author_id": note.author_id,
            "analysis_id": note.analysis_id,
            "note": note.note,
            "created_at": date_str,
        })

    return {
        "notes_count": len(formatted),
        "notes": formatted,
        "evidence_items": evidence_items,
    }
