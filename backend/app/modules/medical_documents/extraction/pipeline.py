"""Medical Document Extraction Pipeline Orchestrator.

Combines Preprocessing, OCR Routing, Medical Entity Extraction, Unit Normalization,
Confidence Calculation, and Status Determination into a unified, reliable workflow.
"""

import time
from typing import List, Optional
from pydantic import BaseModel, Field

from app.modules.medical_documents.extraction.base import OCRResult
from app.modules.medical_documents.extraction.entity_extractor import ExtractedEntity, MedicalEntityExtractor
from app.modules.medical_documents.extraction.router import OCRRouter


class PipelineExtractionResult(BaseModel):
    ocr_result: OCRResult
    entities: List[ExtractedEntity] = Field(default_factory=list)
    final_status: str = "EXTRACTED"  # EXTRACTED or REVIEW_REQUIRED
    processing_time_ms: int = 0
    error: Optional[str] = None


class MedicalExtractionPipeline:
    """Orchestrates document OCR and medical entity extraction."""

    def __init__(self):
        self.router = OCRRouter()
        self.entity_extractor = MedicalEntityExtractor()

    async def process(
        self,
        file_bytes: bytes,
        mime_type: str,
        is_scanned: bool = False,
        has_embedded_text: bool = True,
        preferred_provider: Optional[str] = None,
    ) -> PipelineExtractionResult:
        start_time = time.time()
        try:
            # 1. OCR Routing & Extraction
            provider = self.router.get_provider(
                mime_type=mime_type,
                is_scanned=is_scanned,
                has_embedded_text=has_embedded_text,
                preferred_provider=preferred_provider,
            )
            ocr_result = await provider.extract(file_bytes, mime_type=mime_type)

            # 2. Medical Entity Extraction
            entities = self.entity_extractor.extract_entities(ocr_result)

            # 3. Status Determination
            final_status = "EXTRACTED"
            # If any extracted entity has low confidence, require human review
            for entity in entities:
                if entity.confidence < 0.85:
                    final_status = "REVIEW_REQUIRED"
                    break

            duration_ms = int((time.time() - start_time) * 1000)

            return PipelineExtractionResult(
                ocr_result=ocr_result,
                entities=entities,
                final_status=final_status,
                processing_time_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return PipelineExtractionResult(
                ocr_result=OCRResult(
                    provider="error_handler",
                    provider_version="1.0",
                    raw_text="",
                    blocks=[],
                    tables=[],
                    page_count=1,
                    processing_time_ms=duration_ms,
                ),
                entities=[],
                final_status="FAILED",
                processing_time_ms=duration_ms,
                error=str(e),
            )
