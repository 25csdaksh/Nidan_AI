from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_token
from app.modules.medical_documents.schemas import (
    DocumentExtractionResponse,
    ExtractionEntityResponse,
    MedicalDocumentResponse,
    MedicalDocumentStatusResponse,
    MedicalDocumentUploadResponse,
    PaginatedEntitiesResponse,
    PaginatedMedicalDocumentsResponse,
    ReviewEntityRequest,
)
from app.modules.medical_documents.service import MedicalDocumentService


router = APIRouter()


@router.post(
    "",
    response_model=MedicalDocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Secure Medical Document Ingestion",
)
async def upload_medical_document(
    request: Request,
    patient_id: str = Form(..., description="Target Patient ID"),
    document_type: Optional[str] = Form("UNKNOWN", description="Optional manual modality override"),
    allow_duplicate: bool = Form(False, description="Explicit flag allowing duplicate uploads"),
    file: UploadFile = File(..., description="Medical Document (PDF, PNG, JPG, WEBP)"),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """
    Secure multi-modal medical document ingestion endpoint.
    Performs server-side magic byte validation, SHA-256 integrity calculation,
    encrypted object storage persistence, and task queue dispatch.
    """
    file_bytes = await file.read()
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    service = MedicalDocumentService(db)
    doc, task_id, dup_warning = await service.ingest_document(
        patient_id=patient_id,
        file_bytes=file_bytes,
        original_filename=file.filename or "uploaded_document.pdf",
        client_mime_type=file.content_type,
        explicit_doc_type=document_type,
        current_user=token,
        client_ip=client_ip,
        user_agent=user_agent,
        allow_duplicate=allow_duplicate,
    )

    msg = "Medical document securely stored and queued for processing."
    if dup_warning:
        if allow_duplicate:
            msg = "Document ingested as an intentional duplicate revision."
        else:
            msg = dup_warning.message

    return MedicalDocumentUploadResponse(
        document=MedicalDocumentResponse.model_validate(doc),
        task_id=task_id,
        duplicate_warning=dup_warning,
        message=msg,
    )


@router.get(
    "/{document_id}",
    response_model=MedicalDocumentResponse,
    summary="Get Medical Document Metadata",
)
async def get_document_metadata(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """Retrieves document metadata (never returns raw file bytes by default)."""
    client_ip = request.client.host if request.client else None
    service = MedicalDocumentService(db)
    doc = await service.get_document_metadata(document_id, token, client_ip=client_ip)
    return MedicalDocumentResponse.model_validate(doc)


@router.get(
    "/{document_id}/status",
    response_model=MedicalDocumentStatusResponse,
    summary="Get Document Processing Status",
)
async def get_document_status(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """Returns the real-time processing status and preparation metadata of a document."""
    service = MedicalDocumentService(db)
    doc = await service.get_by_id(document_id, token)
    return MedicalDocumentStatusResponse(
        id=doc.id,
        processing_status=doc.processing_status,
        document_type=doc.document_type,
        page_count=doc.page_count,
        processing_error=doc.processing_error,
        updated_at=doc.updated_at,
        processed_at=doc.processed_at,
        metadata=doc.metadata_json or {},
    )


@router.get(
    "/{document_id}/download",
    summary="Secure Document Download & Stream",
)
async def download_medical_document(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """
    Securely streams raw medical document bytes with authorization check and audit logging.
    Public direct links are strictly prohibited.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    service = MedicalDocumentService(db)
    content, mime_type, filename = await service.get_secure_download_bytes(
        document_id=document_id,
        current_user=token,
        client_ip=client_ip,
        user_agent=user_agent,
    )

    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft Delete Medical Document",
)
async def delete_medical_document(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """Soft deletes a medical document with audit trail preservation."""
    client_ip = request.client.host if request.client else None
    service = MedicalDocumentService(db)
    await service.soft_delete_document(document_id, token, client_ip=client_ip)
    return {"success": True, "message": "Medical document soft-deleted successfully."}


# ---------------------------------------------------------
# PHASE 2: OCR & MEDICAL EXTRACTION ENDPOINTS
# ---------------------------------------------------------

@router.post(
    "/{document_id}/extract",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start / Retry Document OCR Extraction",
)
async def start_document_extraction(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """Triggers or retries asynchronous OCR & structured entity extraction."""
    client_ip = request.client.host if request.client else None
    service = MedicalDocumentService(db)
    task_id = await service.start_document_extraction(document_id, token, client_ip=client_ip)
    return {
        "success": True,
        "message": "Document OCR extraction job queued successfully.",
        "task_id": task_id,
        "document_id": document_id,
    }


@router.get(
    "/{document_id}/extraction",
    response_model=Optional[DocumentExtractionResponse],
    summary="Get Document Extraction Result",
)
async def get_document_extraction(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """Retrieves the full OCR extraction result and structured entities."""
    service = MedicalDocumentService(db)
    extraction = await service.get_document_extraction(document_id, token)
    if not extraction:
        return None
    return DocumentExtractionResponse.model_validate(extraction)


@router.get(
    "/{document_id}/extraction/entities",
    response_model=PaginatedEntitiesResponse,
    summary="Get Extracted Clinical Entities",
)
async def get_extraction_entities(
    document_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    entity_type: Optional[str] = Query(None, description="Optional entity type filter e.g. LAB_ANALYTE"),
    min_confidence: Optional[float] = Query(None, description="Filter by minimum extraction confidence"),
    review_status: Optional[str] = Query(None, description="Filter by review status (PENDING, ACCEPTED, EDITED, REJECTED)"),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """Retrieves paginated clinical entities with provenance and confidence filters."""
    service = MedicalDocumentService(db)
    items, total = await service.get_extraction_entities(
        document_id=document_id,
        current_user=token,
        page=page,
        page_size=page_size,
        entity_type=entity_type,
        min_confidence=min_confidence,
        review_status=review_status,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedEntitiesResponse(
        items=[ExtractionEntityResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch(
    "/{document_id}/extraction/entities/{entity_id}",
    response_model=ExtractionEntityResponse,
    summary="Clinician Review / Edit / Reject Extraction Entity",
)
async def review_extraction_entity(
    request: Request,
    document_id: str,
    entity_id: str,
    payload: ReviewEntityRequest,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """Allows licensed clinicians to verify, edit, or reject extracted medical entities."""
    client_ip = request.client.host if request.client else None
    service = MedicalDocumentService(db)
    updated_entity = await service.review_extraction_entity(
        document_id=document_id,
        entity_id=entity_id,
        review_status=payload.review_status,
        reviewed_value=payload.reviewed_value,
        reviewed_unit=payload.reviewed_unit,
        current_user=token,
        client_ip=client_ip,
    )
    return ExtractionEntityResponse.model_validate(updated_entity)

