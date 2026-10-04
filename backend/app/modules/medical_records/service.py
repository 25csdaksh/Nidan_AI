from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ResourceNotFoundError
from app.modules.medical_records.models import MedicalRecord
from app.modules.medical_records.schemas import MedicalRecordCreate, MedicalRecordUpdate
from app.modules.patients.service import PatientService


class MedicalRecordService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.patient_service = PatientService(db)

    async def get_by_id(self, record_id: str) -> MedicalRecord:
        result = await self.db.execute(select(MedicalRecord).where(MedicalRecord.id == record_id))
        record = result.scalar_one_or_none()
        if not record:
            raise ResourceNotFoundError(f"Medical encounter record '{record_id}' not found.")
        return record

    async def list_by_patient(self, patient_id: str) -> List[MedicalRecord]:
        # Verify patient exists
        await self.patient_service.get_by_id(patient_id)
        stmt = (
            select(MedicalRecord)
            .where(MedicalRecord.patient_id == patient_id)
            .order_by(MedicalRecord.recorded_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_record(self, data: MedicalRecordCreate) -> MedicalRecord:
        await self.patient_service.get_by_id(data.patient_id)
        record = MedicalRecord(
            patient_id=data.patient_id,
            clinician_id=data.clinician_id,
            encounter_type=data.encounter_type,
            chief_complaint=data.chief_complaint,
            clinical_notes=data.clinical_notes,
            vitals=data.vitals,
            status=data.status,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update_record(self, record_id: str, data: MedicalRecordUpdate) -> MedicalRecord:
        record = await self.get_by_id(record_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(record, key, value)
        await self.db.flush()
        await self.db.refresh(record)
        return record
