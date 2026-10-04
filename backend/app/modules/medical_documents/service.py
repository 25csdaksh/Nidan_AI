import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import AppException, ForbiddenError, ResourceNotFoundError
from app.core.logging import logger
from app.core.queue import get_task_broker
from app.core.security import CLINICAL_STAFF_ROLES, UserRole
from app.core.storage import get_storage_service
from app.modules.audit.schemas import AuditLogCreate
from app.modules.audit.service import AuditService
from app.modules.medical_documents.classifier import DocumentClassifier
from app.modules.medical_documents.models import (
    DocumentTypeEnum,
    MedicalDocument,
    ProcessingStatusEnum,
)
from app.modules.medical_documents.schemas import DuplicateWarningInfo
from app.modules.medical_documents.validation import FileSecurityValidator
from app.modules.patients.service import PatientService

if TYPE_CHECKING:
    from app.modules.medical_documents.models import DocumentExtraction, DocumentExtractionEntity


class MedicalDocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.patient_service = PatientService(db)
        self.storage = get_storage_service()
        self.broker = get_task_broker()
        self.audit_service = AuditService(db)

    def check_patient_authorization(self, patient_id: str, current_user: dict):
        """Validates that the authenticated actor has authorization to access the patient's records."""
        user_role = (current_user.get("role") or "").lower()
        user_id = current_user.get("sub")

        # Patients can only access their own linked patient record
        if user_role == UserRole.PATIENT.value.lower():
            linked_patient_id = current_user.get("patient_id") or user_id
            if linked_patient_id != patient_id:
                raise ForbiddenError("Access denied: You are only authorized to access your own medical records.")

        # Clinical staff and admins are authorized
        allowed_role_values = [r.value.lower() for r in CLINICAL_STAFF_ROLES]
        if user_role not in allowed_role_values and user_role != UserRole.SUPER_ADMIN.value.lower() and user_role != UserRole.PATIENT.value.lower():
            raise ForbiddenError("Access denied: Insufficient clinical permissions.")


    async def ingest_document(
        self,
        patient_id: str,
        file_bytes: bytes,
        original_filename: str,
        client_mime_type: Optional[str] = None,
        explicit_doc_type: Optional[str] = None,
        current_user: Optional[dict] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        allow_duplicate: bool = False,
    ) -> Tuple[MedicalDocument, str, Optional[DuplicateWarningInfo]]:
        current_user = current_user or {}
        actor_id = current_user.get("sub")

        # 1. Verify Patient exists and authorization
        await self.patient_service.get_by_id(patient_id)
        self.check_patient_authorization(patient_id, current_user)

        # 2. Audit upload initiated
        await self.audit_service.log_event(
            AuditLogCreate(
                actor_id=actor_id,
                action="MEDICAL_DOCUMENT_UPLOAD_STARTED",
                resource_type="PATIENT",
                resource_id=patient_id,
                ip_address=client_ip,
                user_agent=user_agent,
                details={"original_filename": original_filename, "file_size": len(file_bytes)},
            )
        )

        # 3. Multi-layer File Security Validation
        sanitized_filename, validated_mime, file_size = FileSecurityValidator.validate_document(
            file_bytes=file_bytes,
            original_filename=original_filename,
            client_mime_type=client_mime_type,
        )

        # 4. Server-side SHA-256 Calculation
        server_sha256 = hashlib.sha256(file_bytes).hexdigest()

        # 5. Duplicate Detection for this Patient
        dup_stmt = select(MedicalDocument).where(
            MedicalDocument.patient_id == patient_id,
            MedicalDocument.sha256_hash == server_sha256,
            MedicalDocument.is_deleted == False,
        )
        dup_result = await self.db.execute(dup_stmt)
        existing_doc = dup_result.scalar_one_or_none()

        duplicate_warning = None
        if existing_doc:
            duplicate_warning = DuplicateWarningInfo(
                is_duplicate=True,
                existing_document_id=existing_doc.id,
                existing_filename=existing_doc.original_filename,
                uploaded_at=existing_doc.uploaded_at,
                sha256_hash=server_sha256,
                message=(
                    f"This document appears to have already been uploaded for this patient "
                    f"(Matched existing file: '{existing_doc.original_filename}', uploaded on {existing_doc.uploaded_at.strftime('%Y-%m-%d %H:%M')})."
                ),
            )
            if not allow_duplicate:
                # Return existing document with duplicate warning
                return existing_doc, "duplicate_detected", duplicate_warning

        # 6. Secure Internal Storage Key Generation (No original filename in path)
        doc_uuid = str(uuid.uuid4())
        ext = Path(sanitized_filename).suffix.lower()
        stored_filename = f"{doc_uuid}{ext}"
        storage_key = f"patients/{patient_id}/documents/{doc_uuid}/original{ext}"

        # 7. Secure Storage Ingestion
        saved_key, checksum, stored_size = await self.storage.save_file(
            file_bytes=file_bytes,
            destination_key=storage_key,
            content_type=validated_mime,
        )

        # 8. Initial Safe Modality Classification
        classified_type, confidence, class_meta = DocumentClassifier.classify(
            file_bytes=file_bytes,
            mime_type=validated_mime,
            original_filename=sanitized_filename,
            manual_override=explicit_doc_type,
        )

        # 9. Create DB Record
        doc = MedicalDocument(
            id=doc_uuid,
            patient_id=patient_id,
            uploaded_by=actor_id,
            original_filename=sanitized_filename,
            stored_filename=stored_filename,
            storage_key=saved_key,
            mime_type=validated_mime,
            file_size=stored_size,
            sha256_hash=server_sha256,
            document_type=classified_type.value,
            processing_status=ProcessingStatusEnum.QUEUED.value,
            storage_provider=settings.STORAGE_BACKEND,
            metadata_json={
                "initial_classification": class_meta,
                "confidence": confidence,
                "is_duplicate_override": allow_duplicate and existing_doc is not None,
            },
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)

        # 10. Audit upload completed
        await self.audit_service.log_event(
            AuditLogCreate(
                actor_id=actor_id,
                action="MEDICAL_DOCUMENT_UPLOADED",
                resource_type="MEDICAL_DOCUMENT",
                resource_id=doc.id,
                ip_address=client_ip,
                user_agent=user_agent,
                details={
                    "patient_id": patient_id,
                    "sha256_hash": server_sha256,
                    "document_type": doc.document_type,
                    "file_size": stored_size,
                },
            )
        )

        # 11. Enqueue Background Processing Task
        task_id = await self.broker.enqueue(
            task_name="process_medical_document",
            payload={"document_id": doc.id, "patient_id": patient_id},
        )

        return doc, task_id, duplicate_warning

    async def get_by_id(self, document_id: str, current_user: Optional[dict] = None) -> MedicalDocument:
        stmt = select(MedicalDocument).where(MedicalDocument.id == document_id, MedicalDocument.is_deleted == False)
        result = await self.db.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise ResourceNotFoundError(f"Medical document '{document_id}' not found.")
        if current_user:
            self.check_patient_authorization(doc.patient_id, current_user)
        return doc

    async def get_document_metadata(
        self,
        document_id: str,
        current_user: dict,
        client_ip: Optional[str] = None,
    ) -> MedicalDocument:
        doc = await self.get_by_id(document_id, current_user)
        await self.audit_service.log_event(
            AuditLogCreate(
                actor_id=current_user.get("sub"),
                action="MEDICAL_DOCUMENT_VIEWED",
                resource_type="MEDICAL_DOCUMENT",
                resource_id=doc.id,
                ip_address=client_ip,
                details={"patient_id": doc.patient_id},
            )
        )
        return doc

    async def list_patient_documents(
        self,
        patient_id: str,
        current_user: dict,
        document_type: Optional[str] = None,
        processing_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_desc: bool = True,
    ) -> Tuple[List[MedicalDocument], int]:
        await self.patient_service.get_by_id(patient_id)
        self.check_patient_authorization(patient_id, current_user)

        stmt = select(MedicalDocument).where(
            MedicalDocument.patient_id == patient_id,
            MedicalDocument.is_deleted == False,
        )
        if document_type and document_type.upper() != "ALL":
            stmt = stmt.where(MedicalDocument.document_type == document_type.upper())
        if processing_status and processing_status.upper() != "ALL":
            stmt = stmt.where(MedicalDocument.processing_status == processing_status.upper())

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Pagination & Sorting
        order_clause = MedicalDocument.created_at.desc() if sort_desc else MedicalDocument.created_at.asc()
        stmt = stmt.order_by(order_clause).offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_secure_download_bytes(
        self,
        document_id: str,
        current_user: dict,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bytes, str, str]:
        doc = await self.get_by_id(document_id, current_user)
        file_bytes = await self.storage.get_file_bytes(doc.storage_key)

        await self.audit_service.log_event(
            AuditLogCreate(
                actor_id=current_user.get("sub"),
                action="MEDICAL_DOCUMENT_DOWNLOADED",
                resource_type="MEDICAL_DOCUMENT",
                resource_id=doc.id,
                ip_address=client_ip,
                user_agent=user_agent,
                details={"patient_id": doc.patient_id, "file_size": len(file_bytes)},
            )
        )
        return file_bytes, doc.mime_type, doc.original_filename

    async def soft_delete_document(
        self,
        document_id: str,
        current_user: dict,
        client_ip: Optional[str] = None,
    ) -> bool:
        doc = await self.get_by_id(document_id, current_user)
        user_role = (current_user.get("role") or "").lower()
        if user_role not in [r.value.lower() for r in CLINICAL_STAFF_ROLES] and user_role != UserRole.SUPER_ADMIN.value.lower():
            raise ForbiddenError("Only licensed clinicians and medical administrators can delete medical documents.")

        doc.is_deleted = True
        await self.audit_service.log_event(
            AuditLogCreate(
                actor_id=current_user.get("sub"),
                action="MEDICAL_DOCUMENT_DELETED",
                resource_type="MEDICAL_DOCUMENT",
                resource_id=doc.id,
                ip_address=client_ip,
                details={"patient_id": doc.patient_id, "original_filename": doc.original_filename},
            )
        )
        await self.db.flush()
        return True

    # ---------------------------------------------------------
    # PHASE 2: OCR & MEDICAL EXTRACTION ENGINE
    # ---------------------------------------------------------

    async def start_document_extraction(
        self,
        document_id: str,
        current_user: dict,
        client_ip: Optional[str] = None,
    ) -> str:
        """Manually trigger or retry OCR & structured entity extraction."""
        doc = await self.get_by_id(document_id, current_user)
        user_role = (current_user.get("role") or "").lower()
        if user_role not in [r.value.lower() for r in CLINICAL_STAFF_ROLES] and user_role != UserRole.SUPER_ADMIN.value.lower():
            raise ForbiddenError("Only clinical staff can trigger document extraction.")


        # Update processing status
        doc.processing_status = ProcessingStatusEnum.PROCESSING.value
        await self.db.flush()

        await self.audit_service.log_event(
            AuditLogCreate(
                actor_id=current_user.get("sub"),
                action="MEDICAL_DOCUMENT_EXTRACTION_STARTED",
                resource_type="MEDICAL_DOCUMENT",
                resource_id=doc.id,
                ip_address=client_ip,
                details={"patient_id": doc.patient_id},
            )
        )

        task_id = await self.broker.enqueue(
            task_name="process_medical_document",
            payload={"document_id": doc.id, "patient_id": doc.patient_id, "force_extract": True},
        )
        return task_id

    async def execute_document_extraction(self, document_id: str) -> "DocumentExtraction":
        """Executes full OCR extraction pipeline, stores raw output and canonical medical entities."""
        from app.modules.medical_documents.extraction.pipeline import MedicalExtractionPipeline
        from app.modules.medical_documents.models import DocumentExtraction, DocumentExtractionEntity, ExtractionStatusEnum

        doc = await self.get_by_id(document_id)
        file_bytes = await self.storage.get_file_bytes(doc.storage_key)

        is_scanned = bool(doc.metadata_json.get("is_scanned_document", False))
        has_embedded_text = bool(doc.metadata_json.get("has_embedded_text", True))

        pipeline = MedicalExtractionPipeline()
        res = await pipeline.process(
            file_bytes=file_bytes,
            mime_type=doc.mime_type,
            is_scanned=is_scanned,
            has_embedded_text=has_embedded_text,
        )

        # Check existing extraction
        stmt = select(DocumentExtraction).where(DocumentExtraction.document_id == document_id)
        existing_extraction = (await self.db.execute(stmt)).scalar_one_or_none()

        version = (existing_extraction.extraction_version + 1) if existing_extraction else 1

        if existing_extraction:
            # Delete old entities to keep fresh idempotent state on retry
            del_stmt = select(DocumentExtractionEntity).where(DocumentExtractionEntity.extraction_id == existing_extraction.id)
            old_entities = (await self.db.execute(del_stmt)).scalars().all()
            for old_e in old_entities:
                await self.db.delete(old_e)

            extraction = existing_extraction
            extraction.extraction_version = version
            extraction.provider = res.ocr_result.provider
            extraction.provider_version = res.ocr_result.provider_version
            extraction.status = res.final_status
            extraction.raw_text = res.ocr_result.raw_text
            extraction.raw_blocks = [b.model_dump() for b in res.ocr_result.blocks]
            extraction.raw_tables = [t.model_dump() for t in res.ocr_result.tables]
            extraction.language = res.ocr_result.language
            extraction.page_count = res.ocr_result.page_count
            extraction.processing_time_ms = res.processing_time_ms
            extraction.error = res.error
        else:
            extraction = DocumentExtraction(
                id=str(uuid.uuid4()),
                document_id=document_id,
                extraction_version=version,
                provider=res.ocr_result.provider,
                provider_version=res.ocr_result.provider_version,
                status=res.final_status,
                raw_text=res.ocr_result.raw_text,
                raw_blocks=[b.model_dump() for b in res.ocr_result.blocks],
                raw_tables=[t.model_dump() for t in res.ocr_result.tables],

                language=res.ocr_result.language,
                page_count=res.ocr_result.page_count,
                processing_time_ms=res.processing_time_ms,
                error=res.error,
            )
            self.db.add(extraction)

        await self.db.flush()

        # Insert extracted clinical entities
        for ent in res.entities:
            entity_model = DocumentExtractionEntity(
                id=str(uuid.uuid4()),
                extraction_id=extraction.id,
                document_id=document_id,
                entity_type=ent.entity_type,
                raw_name=ent.raw_name,
                canonical_name=ent.canonical_name,
                value_text=ent.value_text,
                numeric_value=ent.numeric_value,
                original_unit=ent.original_unit,
                normalized_unit=ent.normalized_unit,
                reference_range_text=ent.reference_range_text,
                reference_min=ent.reference_min,
                reference_max=ent.reference_max,
                technical_status=ent.technical_status,
                confidence=ent.confidence,
                page_number=ent.page_number,
                bounding_box=ent.bounding_box,
                source_text=ent.source_text,
            )
            self.db.add(entity_model)

        # Update document state
        doc.processing_status = ProcessingStatusEnum.COMPLETED.value
        doc.processed_at = datetime.now(timezone.utc)
        doc.page_count = res.ocr_result.page_count
        doc.metadata_json["extraction_id"] = extraction.id
        doc.metadata_json["extracted_entities_count"] = len(res.entities)

        await self.audit_service.log_event(
            AuditLogCreate(
                actor_id=doc.uploaded_by,
                action="MEDICAL_DOCUMENT_EXTRACTION_COMPLETED",
                resource_type="DOCUMENT_EXTRACTION",
                resource_id=extraction.id,
                details={
                    "document_id": document_id,
                    "entities_count": len(res.entities),
                    "status": extraction.status,
                },
            )
        )

        await self.db.flush()
        await self.db.refresh(extraction)
        return extraction

    async def get_document_extraction(
        self,
        document_id: str,
        current_user: dict,
    ) -> Optional["DocumentExtraction"]:
        from app.modules.medical_documents.models import DocumentExtraction, DocumentExtractionEntity
        from sqlalchemy.orm import selectinload

        doc = await self.get_by_id(document_id, current_user)
        stmt = (
            select(DocumentExtraction)
            .where(DocumentExtraction.document_id == document_id)
            .options(selectinload(DocumentExtraction.entities))
            .order_by(DocumentExtraction.extraction_version.desc())
        )
        result = await self.db.execute(stmt)
        extraction = result.scalars().first()
        return extraction

    async def get_extraction_entities(
        self,
        document_id: str,
        current_user: dict,
        page: int = 1,
        page_size: int = 50,
        entity_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        review_status: Optional[str] = None,
    ) -> Tuple[List["DocumentExtractionEntity"], int]:
        from app.modules.medical_documents.models import DocumentExtractionEntity

        doc = await self.get_by_id(document_id, current_user)
        stmt = select(DocumentExtractionEntity).where(DocumentExtractionEntity.document_id == document_id)

        if entity_type and entity_type.upper() != "ALL":
            stmt = stmt.where(DocumentExtractionEntity.entity_type == entity_type.upper())
        if min_confidence is not None:
            stmt = stmt.where(DocumentExtractionEntity.confidence >= min_confidence)
        if review_status and review_status.upper() != "ALL":
            stmt = stmt.where(DocumentExtractionEntity.review_status == review_status.upper())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(DocumentExtractionEntity.page_number.asc(), DocumentExtractionEntity.canonical_name.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def review_extraction_entity(
        self,
        document_id: str,
        entity_id: str,
        review_status: str,
        reviewed_value: Optional[str],
        reviewed_unit: Optional[str],
        current_user: dict,
        client_ip: Optional[str] = None,
    ) -> "DocumentExtractionEntity":
        from app.modules.medical_documents.models import (
            DocumentExtraction,
            DocumentExtractionEntity,
            EntityReviewStatusEnum,
            ExtractionStatusEnum,
        )

        doc = await self.get_by_id(document_id, current_user)
        user_role = (current_user.get("role") or "").lower()
        if user_role not in [r.value.lower() for r in CLINICAL_STAFF_ROLES] and user_role != UserRole.SUPER_ADMIN.value.lower():
            raise ForbiddenError("Only licensed clinicians can review and verify medical extractions.")


        stmt = select(DocumentExtractionEntity).where(
            DocumentExtractionEntity.id == entity_id,
            DocumentExtractionEntity.document_id == document_id,
        )
        entity = (await self.db.execute(stmt)).scalar_one_or_none()
        if not entity:
            raise ResourceNotFoundError(f"Extraction entity '{entity_id}' not found.")

        # Store prior values for audit log
        prior_state = {
            "review_status": entity.review_status,
            "reviewed_value": entity.reviewed_value,
            "normalized_unit": entity.normalized_unit,
        }

        # Apply review changes
        valid_statuses = [s.value for s in EntityReviewStatusEnum]
        if review_status.upper() not in valid_statuses:
            raise AppException(f"Invalid review status: '{review_status}'. Must be one of {valid_statuses}")

        entity.review_status = review_status.upper()
        if reviewed_value is not None:
            entity.reviewed_value = reviewed_value.strip()
        if reviewed_unit is not None:
            entity.normalized_unit = reviewed_unit.strip()

        entity.reviewed_by = current_user.get("sub")
        entity.reviewed_at = datetime.now(timezone.utc)

        # Audit event
        await self.audit_service.log_event(
            AuditLogCreate(
                actor_id=current_user.get("sub"),
                action="MEDICAL_DOCUMENT_EXTRACTION_REVIEWED",
                resource_type="EXTRACTION_ENTITY",
                resource_id=entity.id,
                ip_address=client_ip,
                details={
                    "document_id": document_id,
                    "canonical_name": entity.canonical_name,
                    "prior_state": prior_state,
                    "new_status": entity.review_status,
                    "reviewed_value": entity.reviewed_value,
                },
            )
        )

        # Check if all entities in this extraction are reviewed
        all_entities_stmt = select(DocumentExtractionEntity).where(
            DocumentExtractionEntity.extraction_id == entity.extraction_id
        )
        all_ents = (await self.db.execute(all_entities_stmt)).scalars().all()
        all_reviewed = all(e.review_status in [EntityReviewStatusEnum.ACCEPTED.value, EntityReviewStatusEnum.EDITED.value, EntityReviewStatusEnum.REJECTED.value] for e in all_ents)

        if all_reviewed:
            ext_stmt = select(DocumentExtraction).where(DocumentExtraction.id == entity.extraction_id)
            extraction = (await self.db.execute(ext_stmt)).scalar_one_or_none()
            if extraction:
                extraction.status = ExtractionStatusEnum.REVIEWED.value

        await self.db.flush()
        await self.db.refresh(entity)
        return entity
