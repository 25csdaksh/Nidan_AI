from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class OCRTextBlock(BaseModel):
    page: int
    text: str
    confidence: float = 1.0
    bounding_box: Optional[BoundingBox] = None
    line_number: Optional[int] = None


class OCRTable(BaseModel):
    page: int
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)
    confidence: float = 1.0


class OCRResult(BaseModel):
    provider: str
    provider_version: str
    raw_text: str
    blocks: List[OCRTextBlock] = Field(default_factory=list)
    tables: List[OCRTable] = Field(default_factory=list)
    language: str = "en"
    page_count: int = 1
    processing_time_ms: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseOCRProvider(ABC):
    """Abstract base class for OCR and document text extraction providers."""

    @abstractmethod
    async def extract(self, file_bytes: bytes, mime_type: str, **kwargs) -> OCRResult:
        """Extract text, blocks, and tables from raw document bytes."""
        pass
