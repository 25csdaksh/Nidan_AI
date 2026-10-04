from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ResourceNotFoundError
from app.modules.prescriptions.models import Prescription
from app.modules.prescriptions.schemas import PrescriptionCreate, PrescriptionUpdate


class PrescriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, rx_id: str) -> Prescription:
        result = await self.db.execute(select(Prescription).where(Prescription.id == rx_id))
        rx = result.scalar_one_or_none()
        if not rx:
            raise ResourceNotFoundError(f"Prescription record '{rx_id}' not found.")
        return rx

    async def list_by_patient(self, patient_id: str, only_active: bool = False) -> List[Prescription]:
        stmt = select(Prescription).where(Prescription.patient_id == patient_id)
        if only_active:
            stmt = stmt.where(Prescription.is_active == True)
        stmt = stmt.order_by(Prescription.prescribed_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_prescription(self, data: PrescriptionCreate) -> Prescription:
        rx = Prescription(
            patient_id=data.patient_id,
            report_id=data.report_id,
            drug_name=data.drug_name,
            generic_name=data.generic_name,
            dosage=data.dosage,
            frequency=data.frequency,
            route=data.route,
            duration_days=data.duration_days,
            instructions=data.instructions,
            is_active=data.is_active,
        )
        self.db.add(rx)
        await self.db.flush()
        await self.db.refresh(rx)
        return rx

    async def update_prescription(self, rx_id: str, data: PrescriptionUpdate) -> Prescription:
        rx = await self.get_by_id(rx_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rx, key, value)
        await self.db.flush()
        await self.db.refresh(rx)
        return rx
