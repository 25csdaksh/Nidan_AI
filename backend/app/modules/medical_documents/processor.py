import io
from datetime import datetime, timezone
from typing import Optional
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.core.storage import get_storage_service
from app.modules.audit.schemas import AuditLogCreate
from app.modules.audit.service import AuditService
from app.modules.medical_documents.classifier import DocumentClassifier
from app.modules.medical_documents.models import DocumentTypeEnum, MedicalDocument, ProcessingStatusEnum


async def _execute_document_processing(doc_id: str, db: AsyncSession):
    storage = get_storage_service()
    audit_service = AuditService(db)

    # 1. Fetch Document Record
    stmt = select(MedicalDocument).where(MedicalDocument.id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc or doc.is_deleted:
        logger.warning("Document %s not found or deleted, skipping processing.", doc_id)
        return

    # 2. Update status to PROCESSING & Log Audit
    doc.processing_status = ProcessingStatusEnum.PROCESSING.value
    await audit_service.log_event(
        AuditLogCreate(
            actor_id=doc.uploaded_by,
            action="MEDICAL_DOCUMENT_PROCESSING_STARTED",
            resource_type="MEDICAL_DOCUMENT",
            resource_id=doc.id,
            details={"patient_id": doc.patient_id, "mime_type": doc.mime_type},
        )
    )
    await db.flush()

    try:
        # 3. Retrieve stored file bytes
        file_bytes = await storage.get_file_bytes(doc.storage_key)

        # 4. Extract structural metadata & classify
        meta = dict(doc.metadata_json or {})
        page_count = doc.page_count or 1

        if doc.mime_type == "application/pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            page_count = len(reader.pages)
            total_text_len = 0
            for p in reader.pages[:10]:
                txt = p.extract_text() or ""
                total_text_len += len(txt.strip())

            has_text = total_text_len > 15
            is_scanned = total_text_len < (25 * max(1, min(page_count, 10)))

            meta.update({
                "page_count": page_count,
                "has_embedded_text": has_text,
                "is_scanned_document": is_scanned,
                "pdf_version": getattr(reader, "pdf_header", "PDF-1.x"),
            })
        else:
            # Image inspection
            with Image.open(io.BytesIO(file_bytes)) as img:
                width, height = img.size
                meta.update({
                    "image_width": width,
                    "image_height": height,
                    "image_format": img.format,
                    "image_mode": img.mode,
                })

        # 6. Classify modality if currently UNKNOWN
        if doc.document_type == DocumentTypeEnum.UNKNOWN.value:
            classified_type, confidence, details = DocumentClassifier.classify(
                file_bytes=file_bytes,
                mime_type=doc.mime_type,
                original_filename=doc.original_filename,
            )
            doc.document_type = classified_type.value
            meta["classification_details"] = details
            meta["classification_confidence"] = confidence

        doc.page_count = page_count
        doc.metadata_json = meta
        await db.flush()

        # 7. Execute Phase 2 OCR & Medical Extraction Pipeline
        from app.modules.medical_documents.service import MedicalDocumentService
        doc_service = MedicalDocumentService(db)
        extraction = await doc_service.execute_document_extraction(doc.id)

        # 8. Finalize record as COMPLETED
        doc.processing_status = ProcessingStatusEnum.COMPLETED.value
        doc.processed_at = datetime.now(timezone.utc)
        doc.processing_error = None

        await audit_service.log_event(
            AuditLogCreate(
                actor_id=doc.uploaded_by,
                action="MEDICAL_DOCUMENT_PROCESSING_COMPLETED",
                resource_type="MEDICAL_DOCUMENT",
                resource_id=doc.id,
                details={
                    "patient_id": doc.patient_id,
                    "document_type": doc.document_type,
                    "page_count": page_count,
                    "extraction_id": extraction.id,
                    "extraction_status": extraction.status,
                },
            )
        )
        await db.flush()
        logger.info("Successfully processed document %s (type: %s, pages: %s, extraction: %s)", doc_id, doc.document_type, page_count, extraction.status)

    except Exception as e:
        logger.error("Failed processing document %s: %s", doc_id, str(e), exc_info=True)
        doc.processing_status = ProcessingStatusEnum.FAILED.value
        doc.processing_error = f"Ingestion preparation failed: {str(e)}"
        doc.processed_at = datetime.now(timezone.utc)

        await audit_service.log_event(
            AuditLogCreate(
                actor_id=doc.uploaded_by,
                action="MEDICAL_DOCUMENT_PROCESSING_FAILED",
                resource_type="MEDICAL_DOCUMENT",
                resource_id=doc.id,
                details={"error": str(e), "patient_id": doc.patient_id},
            )
        )
        await db.flush()


async def process_medical_document_task(document_id: str, session: Optional[AsyncSession] = None):
    """
    Background worker task for document preparation and structured medical extraction.
    Strictly extracts verifiable facts and canonical parameters without disease diagnosis.
    """
    logger.info("Worker starting document preparation and extraction for %s...", document_id)
    if session is not None:
        await _execute_document_processing(document_id, session)
    else:
        async with AsyncSessionLocal() as db:
            await _execute_document_processing(document_id, db)
            await db.commit()

