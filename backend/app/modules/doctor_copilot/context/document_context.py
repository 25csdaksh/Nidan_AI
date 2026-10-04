from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.modules.medical_documents.models import MedicalDocument
from app.modules.doctor_copilot.schemas import EvidenceItem, EvidenceType


async def build_document_context(
    session: AsyncSession,
    patient_id: str,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Retrieves uploaded medical documents and processing status for the patient.
    """
    stmt = (
        select(MedicalDocument)
        .where(MedicalDocument.patient_id == patient_id, MedicalDocument.is_deleted == False)
        .order_by(desc(MedicalDocument.uploaded_at))
        .limit(limit)
    )
    res = await session.execute(stmt)
    documents = res.scalars().all()

    evidence_items: List[EvidenceItem] = []
    formatted: List[Dict[str, Any]] = []

    for idx, doc in enumerate(documents):
        ev_id = f"EVID-DOC-{idx+1}"
        date_str = doc.uploaded_at.strftime("%Y-%m-%d") if doc.uploaded_at else "UNKNOWN"
        evidence_items.append(
            EvidenceItem(
                evidence_id=ev_id,
                type=EvidenceType.DOCUMENT,
                patient_id=patient_id,
                document_id=doc.id,
                date=date_str,
                title=f"Medical Document: {doc.original_filename}",
                value=doc.document_type,
                status=doc.processing_status,
                details={
                    "filename": doc.original_filename,
                    "document_type": doc.document_type,
                    "page_count": doc.page_count,
                    "mime_type": doc.mime_type,
                    "sha256": doc.sha256_hash,
                }
            )
        )
        formatted.append({
            "evidence_id": ev_id,
            "id": doc.id,
            "filename": doc.original_filename,
            "document_type": doc.document_type,
            "uploaded_at": date_str,
            "processing_status": doc.processing_status,
            "page_count": doc.page_count,
        })

    return {
        "documents_count": len(formatted),
        "documents": formatted,
        "evidence_items": evidence_items,
    }
