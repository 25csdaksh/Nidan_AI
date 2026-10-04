import abc
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ClinicalInsightItem(BaseModel):
    category: str  # LAB_ABNORMALITY, POTENTIAL_DEFICIENCY, CRITICAL_FINDING, PATTERN_CORRELATION
    title: str
    description: str
    severity: str  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    evidence_span: Optional[str] = None
    confidence_score: float
    source_reference: Optional[str] = None


class ClinicalSummaryDraft(BaseModel):
    disclaimer: str
    chief_extracted_points: List[str]
    abnormalities: List[ClinicalInsightItem]
    deficiencies: List[ClinicalInsightItem]
    critical_flags: List[ClinicalInsightItem]
    review_status: str = "PENDING_DOCTOR_VERIFICATION"


class BaseClinicalExtractor(abc.ABC):
    """Abstract interface for modality-specific clinical extractors."""

    @abc.abstractmethod
    async def extract_and_analyze(self, file_bytes: bytes, metadata: Dict[str, Any]) -> ClinicalSummaryDraft:
        """Processes document and produces structured clinical insight candidates."""
        pass

    @abc.abstractmethod
    def get_pipeline_version(self) -> str:
        """Returns the model/pipeline semver."""
        pass
