from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AppException, ResourceNotFoundError
from app.modules.patients.models import Patient
from app.modules.patients.schemas import PatientCreate, PatientUpdate


class PatientService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, patient_id: str) -> Patient:
        result = await self.db.execute(select(Patient).where(Patient.id == patient_id))
        patient = result.scalar_one_or_none()
        if not patient:
            raise ResourceNotFoundError(f"Patient record '{patient_id}' not found.")
        return patient

    async def get_by_mrn(self, mrn: str) -> Optional[Patient]:
        result = await self.db.execute(select(Patient).where(Patient.mrn == mrn))
        return result.scalar_one_or_none()

    async def search_patients(self, query: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[Patient]:
        stmt = select(Patient)
        if query:
            q = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Patient.mrn.ilike(q),
                    Patient.first_name.ilike(q),
                    Patient.last_name.ilike(q),
                    Patient.phone.ilike(q),
                )
            )
        stmt = stmt.order_by(Patient.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_patient(self, data: PatientCreate) -> Patient:
        existing = await self.get_by_mrn(data.mrn)
        if existing:
            raise AppException(f"A patient with MRN '{data.mrn}' already exists.", code="MRN_EXISTS", status_code=400)

        patient = Patient(
            mrn=data.mrn,
            first_name=data.first_name,
            last_name=data.last_name,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            blood_group=data.blood_group,
            phone=data.phone,
            email=data.email,
            address=data.address,
            known_allergies=data.known_allergies,
            chronic_conditions=data.chronic_conditions,
        )
        self.db.add(patient)
        await self.db.flush()
        await self.db.refresh(patient)
        return patient

    async def update_patient(self, patient_id: str, data: PatientUpdate) -> Patient:
        patient = await self.get_by_id(patient_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(patient, key, value)
        await self.db.flush()
        await self.db.refresh(patient)
        return patient
