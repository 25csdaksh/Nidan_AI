"""OCR Dynamic Router.

Directs document payloads to the optimal extraction provider based on MIME type
and Phase 1 metadata (embedded text vs scanned image vs camera photo).
"""

from typing import Optional
from app.modules.medical_documents.extraction.base import BaseOCRProvider
from app.modules.medical_documents.extraction.providers import (
    DevelopmentOCRProvider,
    PDFTextExtractor,
    TesseractOCRProvider,
)


class OCRRouter:
    """Intelligently routes documents to appropriate text/OCR extraction providers."""

    def __init__(self):
        self.pdf_text_extractor = PDFTextExtractor()
        self.tesseract_provider = TesseractOCRProvider()
        self.dev_provider = DevelopmentOCRProvider()

    def get_provider(
        self,
        mime_type: str,
        is_scanned: bool = False,
        has_embedded_text: bool = True,
        preferred_provider: Optional[str] = None,
    ) -> BaseOCRProvider:
        # If user explicitly preferred development provider
        if preferred_provider == "dev":
            return self.dev_provider

        # PDF Routing logic
        if mime_type == "application/pdf":
            if has_embedded_text and not is_scanned:
                return self.pdf_text_extractor
            else:
                # Scanned PDF requires OCR
                return self.tesseract_provider

        # Image Formats (PNG, JPEG, WEBP)
        if mime_type in ["image/png", "image/jpeg", "image/webp", "image/jpg"]:
            return self.dev_provider

        # Default fallback
        return self.dev_provider
