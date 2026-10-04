from typing import List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clinical_intelligence.models import ReferenceRange
from app.modules.clinical_intelligence.reference_ranges.catalog import (
    REFERENCE_RANGE_CATALOG,
    ReferenceRangeDefinition,
)
from app.modules.clinical_intelligence.reference_ranges.schemas import ReferenceRangeCreate


class ReferenceRangeRepository:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def get_by_id(self, range_id: str) -> Optional[ReferenceRange]:
        if not self.db:
            return None
        result = await self.db.execute(select(ReferenceRange).where(ReferenceRange.id == range_id))
        return result.scalars().first()

    async def list_ranges(
        self,
        panel: Optional[str] = None,
        canonical_name: Optional[str] = None,
        sex: Optional[str] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ReferenceRange]:
        if not self.db:
            # Fall back to catalog definitions converted to objects
            results = []
            for item in REFERENCE_RANGE_CATALOG:
                if panel and item.panel.lower() != panel.lower():
                    continue
                if canonical_name and item.canonical_name.lower() != canonical_name.lower():
                    continue
                if sex and item.sex.lower() not in (sex.lower(), "all"):
                    continue
                results.append(item)
            return results[skip : skip + limit]

        query = select(ReferenceRange).where(ReferenceRange.is_active == is_active)
        if panel:
            query = query.where(ReferenceRange.panel == panel)
        if canonical_name:
            query = query.where(ReferenceRange.canonical_name == canonical_name)
        if sex:
            query = query.where(or_(ReferenceRange.sex == sex, ReferenceRange.sex == "all"))
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def seed_from_catalog(self) -> int:
        """Seed DB table from static catalog if empty."""
        if not self.db:
            return 0
        existing = await self.db.execute(select(ReferenceRange).limit(1))
        if existing.scalars().first() is not None:
            return 0

        count = 0
        for defn in REFERENCE_RANGE_CATALOG:
            rr = ReferenceRange(
                analyte=defn.analyte,
                canonical_name=defn.canonical_name,
                panel=defn.panel,
                sex=defn.sex,
                age_min=defn.age_min,
                age_max=defn.age_max,
                pregnancy_status=defn.pregnancy_status,
                unit=defn.unit,
                lower_bound=defn.lower_bound,
                upper_bound=defn.upper_bound,
                lower_operator=defn.lower_operator,
                upper_operator=defn.upper_operator,
                critical_low=defn.critical_low,
                critical_high=defn.critical_high,
                source_name=defn.source_name,
                source_version=defn.source_version,
                source_url=defn.source_url,
                effective_from="2026-01-01",
                version=1,
                notes=defn.notes,
                is_active=True,
            )
            self.db.add(rr)
            count += 1
        await self.db.commit()
        return count
