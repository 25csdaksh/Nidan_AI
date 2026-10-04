from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.lab.models import LabResult
from app.modules.lab.schemas import LabResultCreate, LabTrendItem, LabTrendResponse


class LabService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_patient(
        self,
        patient_id: str,
        only_abnormal: bool = False,
        panel_name: Optional[str] = None,
    ) -> List[LabResult]:
        stmt = select(LabResult).where(LabResult.patient_id == patient_id)
        if only_abnormal:
            stmt = stmt.where(LabResult.is_abnormal == True)
        if panel_name:
            stmt = stmt.where(LabResult.panel_name.ilike(f"%{panel_name}%"))
        stmt = stmt.order_by(LabResult.recorded_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_report(self, report_id: str) -> List[LabResult]:
        stmt = select(LabResult).where(LabResult.report_id == report_id).order_by(LabResult.analyte_name.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_longitudinal_trend(self, patient_id: str, analyte_name: str) -> LabTrendResponse:
        stmt = (
            select(LabResult)
            .where(
                LabResult.patient_id == patient_id,
                LabResult.analyte_name.ilike(analyte_name),
                LabResult.value_numeric != None,
            )
            .order_by(LabResult.recorded_at.asc())
        )
        result = await self.db.execute(stmt)
        records = list(result.scalars().all())

        trends = [
            LabTrendItem(
                recorded_at=r.recorded_at,
                value=r.value_numeric,
                unit=r.unit,
                is_abnormal=r.is_abnormal,
            )
            for r in records
        ]

        ref_low = records[0].ref_low if records else None
        ref_high = records[0].ref_high if records else None
        unit = records[0].unit if records else None

        return LabTrendResponse(
            patient_id=patient_id,
            analyte_name=analyte_name,
            unit=unit,
            ref_low=ref_low,
            ref_high=ref_high,
            trends=trends,
        )

    async def record_batch(self, items: List[LabResultCreate]) -> List[LabResult]:
        results = []
        for item in items:
            # Auto compute abnormality if reference ranges provided
            is_abnormal = item.is_abnormal
            interpretation = item.interpretation or "NORMAL"
            if item.value_numeric is not None:
                if item.ref_low is not None and item.value_numeric < item.ref_low:
                    is_abnormal = True
                    interpretation = "LOW"
                elif item.ref_high is not None and item.value_numeric > item.ref_high:
                    is_abnormal = True
                    interpretation = "HIGH"

            rec = LabResult(
                patient_id=item.patient_id,
                report_id=item.report_id,
                panel_name=item.panel_name,
                analyte_name=item.analyte_name,
                loinc_code=item.loinc_code,
                value_numeric=item.value_numeric,
                value_text=item.value_text,
                unit=item.unit,
                ref_low=item.ref_low,
                ref_high=item.ref_high,
                interpretation=interpretation,
                is_abnormal=is_abnormal,
                is_critical=item.is_critical,
            )
            self.db.add(rec)
            results.append(rec)

        await self.db.flush()
        return results
