from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FindingEvidenceItem(BaseModel):
    entity_id: Optional[str] = None
    analyte: str
    value: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    status: Optional[str] = None
    page_number: Optional[int] = None
    source_text: Optional[str] = None
    confidence: float = 1.0
    review_status: str = "PENDING"


class EvidenceProvenanceBuilder:
    @staticmethod
    def build_evidence_item(
        entity_id: Optional[str],
        analyte: str,
        value: str,
        numeric_value: Optional[float],
        unit: Optional[str],
        status: Optional[str] = None,
        page_number: Optional[int] = None,
        source_text: Optional[str] = None,
        confidence: float = 1.0,
        review_status: str = "PENDING",
    ) -> Dict[str, Any]:
        return FindingEvidenceItem(
            entity_id=entity_id,
            analyte=analyte,
            value=value,
            numeric_value=numeric_value,
            unit=unit,
            status=status,
            page_number=page_number,
            source_text=source_text,
            confidence=round(confidence, 2),
            review_status=review_status,
        ).model_dump()
