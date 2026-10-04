import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ResourceNotFoundError
from app.core.queue import get_task_broker
from app.core.storage import get_storage_service
from app.modules.patients.service import PatientService
from app.modules.reports.models import DocumentType, ExtractionStatus, Report
from app.modules.reports.schemas import ReportCreate, ReportUpdate


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.patient_service = PatientService(db)
        self.storage = get_storage_service()
        self.broker = get_task_broker()

    async def get_by_id(self, report_id: str) -> Report:
        result = await self.db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            raise ResourceNotFoundError(f"Clinical report '{report_id}' not found.")
        return report

    async def list_by_patient(self, patient_id: str) -> List[Report]:
        await self.patient_service.get_by_id(patient_id)
        stmt = select(Report).where(Report.patient_id == patient_id).order_by(Report.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 50) -> List[Report]:
        stmt = select(Report).order_by(Report.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def ingest_file(
        self,
        patient_id: str,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        document_type: DocumentType,
        medical_record_id: Optional[str] = None,
    ) -> tuple[Report, str]:
        await self.patient_service.get_by_id(patient_id)

        # 1. Save to Object Storage
        file_uuid = uuid.uuid4()
        storage_key = f"patients/{patient_id}/reports/{file_uuid}_{filename}"
        saved_key, checksum, size = await self.storage.save_file(
            file_bytes=file_bytes,
            destination_key=storage_key,
            content_type=content_type,
        )

        # 2. Create Database Record
        report = Report(
            patient_id=patient_id,
            medical_record_id=medical_record_id,
            document_type=document_type.value,
            file_name=filename,
            storage_key=saved_key,
            mime_type=content_type,
            file_size_bytes=size,
            checksum_sha256=checksum,
            extraction_status=ExtractionStatus.PENDING.value,
            metadata_json={"original_filename": filename},
        )
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)

        # 3. Queue Background Extraction Pipeline
        task_id = await self.broker.enqueue(
            task_name="extract_medical_document",
            payload={
                "report_id": report.id,
                "patient_id": patient_id,
                "document_type": document_type.value,
                "storage_key": saved_key,
            },
        )

        return report, task_id
