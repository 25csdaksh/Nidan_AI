from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ResourceNotFoundError
from app.modules.imaging.models import ImagingStudy
from app.modules.imaging.schemas import ImagingStudyCreate


class ImagingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, study_id: str) -> ImagingStudy:
        result = await self.db.execute(select(ImagingStudy).where(ImagingStudy.id == study_id))
        study = result.scalar_one_or_none()
        if not study:
            raise ResourceNotFoundError(f"Imaging study '{study_id}' not found.")
        return study

    async def list_by_patient(self, patient_id: str) -> List[ImagingStudy]:
        stmt = select(ImagingStudy).where(ImagingStudy.patient_id == patient_id).order_by(ImagingStudy.performed_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_study(self, data: ImagingStudyCreate) -> ImagingStudy:
        study = ImagingStudy(
            patient_id=data.patient_id,
            report_id=data.report_id,
            modality=data.modality.upper(),
            body_part=data.body_part,
            view_position=data.view_position,
            dicom_series_uid=data.dicom_series_uid,
            radiologist_impression=data.radiologist_impression,
            structured_findings=data.structured_findings,
        )
        self.db.add(study)
        await self.db.flush()
        await self.db.refresh(study)
        return study
