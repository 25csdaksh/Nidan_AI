"""OCR and Document Text Extraction Providers.

Provides standard implementations for PDF text extraction, Tesseract OCR,
development fallback providers, and production cloud OCR interfaces.
"""

import io
import time
from typing import Any, Dict, List, Optional
from pypdf import PdfReader
from PIL import Image

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

from app.modules.medical_documents.extraction.base import (
    BaseOCRProvider,
    BoundingBox,
    OCRResult,
    OCRTable,
    OCRTextBlock,
)


class PDFTextExtractor(BaseOCRProvider):
    """Direct text extractor for born-digital PDF documents using pypdf."""

    async def extract(self, file_bytes: bytes, mime_type: str = "application/pdf", **kwargs) -> OCRResult:
        start_time = time.time()
        stream = io.BytesIO(file_bytes)
        reader = PdfReader(stream)
        
        blocks: List[OCRTextBlock] = []
        raw_text_parts: List[str] = []
        page_count = len(reader.pages)

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            extracted_page_text = page.extract_text() or ""
            raw_text_parts.append(extracted_page_text)
            
            lines = extracted_page_text.splitlines()
            for line_idx, line in enumerate(lines):
                cleaned_line = line.strip()
                if cleaned_line:
                    blocks.append(
                        OCRTextBlock(
                            page=page_num,
                            text=cleaned_line,
                            confidence=0.98,
                            line_number=line_idx + 1,
                        )
                    )

        raw_text = "\n\n".join(raw_text_parts)
        duration_ms = int((time.time() - start_time) * 1000)

        return OCRResult(
            provider="local_pdf_text_extractor",
            provider_version="pypdf-4.0",
            raw_text=raw_text,
            blocks=blocks,
            tables=[],
            language="en",
            page_count=max(page_count, 1),
            processing_time_ms=duration_ms,
            metadata={"total_lines": len(blocks)},
        )


class TesseractOCRProvider(BaseOCRProvider):
    """Image OCR provider utilizing Tesseract OCR."""

    async def extract(self, file_bytes: bytes, mime_type: str = "image/png", **kwargs) -> OCRResult:
        start_time = time.time()
        blocks: List[OCRTextBlock] = []
        raw_text = ""

        try:
            image = Image.open(io.BytesIO(file_bytes))
            if not PYTESSERACT_AVAILABLE:
                raise RuntimeError("pytesseract package is not available")
            
            raw_text = pytesseract.image_to_string(image)
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            n_boxes = len(data["text"])
            current_line_text: List[str] = []
            current_line_num = -1
            current_page = 1

            for i in range(n_boxes):
                word = data["text"][i].strip()
                conf = float(data["conf"][i]) if float(data["conf"][i]) > 0 else 0.5
                line_num = data["line_num"][i]
                page_num = data.get("page_num", [1])[i]

                if word:
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    blocks.append(
                        OCRTextBlock(
                            page=page_num,
                            text=word,
                            confidence=min(conf / 100.0, 1.0),
                            bounding_box=BoundingBox(x=x, y=y, width=w, height=h),
                            line_number=line_num,
                        )
                    )
        except Exception as e:
            # Fallback or propagate error
            raw_text = raw_text or ""
            duration_ms = int((time.time() - start_time) * 1000)
            return OCRResult(
                provider="tesseract_ocr",
                provider_version="pytesseract",
                raw_text=raw_text,
                blocks=blocks,
                tables=[],
                language="en",
                page_count=1,
                processing_time_ms=duration_ms,
                metadata={"error": str(e)},
            )

        duration_ms = int((time.time() - start_time) * 1000)
        return OCRResult(
            provider="tesseract_ocr",
            provider_version="pytesseract",
            raw_text=raw_text,
            blocks=blocks,
            tables=[],
            language="en",
            page_count=1,
            processing_time_ms=duration_ms,
            metadata={"words_detected": len(blocks)},
        )


class DevelopmentOCRProvider(BaseOCRProvider):
    """Robust development provider supporting PDF and image OCR with safe heuristics."""

    def __init__(self):
        self.pdf_extractor = PDFTextExtractor()
        self.tesseract_provider = TesseractOCRProvider()

    async def extract(self, file_bytes: bytes, mime_type: str, **kwargs) -> OCRResult:
        if mime_type == "application/pdf":
            # Direct PDF parsing
            return await self.pdf_extractor.extract(file_bytes, mime_type, **kwargs)

        # Image parsing: attempt Tesseract first
        if PYTESSERACT_AVAILABLE:
            try:
                res = await self.tesseract_provider.extract(file_bytes, mime_type, **kwargs)
                if res.raw_text and len(res.raw_text.strip()) > 0:
                    return res
            except Exception:
                pass

        # Safe fallback for development/test environment without tesseract binary installed
        start_time = time.time()
        img = Image.open(io.BytesIO(file_bytes))
        width, height = img.size
        duration_ms = int((time.time() - start_time) * 1000)

        return OCRResult(
            provider="dev_image_processor",
            provider_version="pillow-10.0",
            raw_text=f"[Image Document {width}x{height} - Format: {img.format}]",
            blocks=[
                OCRTextBlock(
                    page=1,
                    text=f"[Image Document {width}x{height}]",
                    confidence=0.85,
                    bounding_box=BoundingBox(x=0, y=0, width=width, height=height),
                    line_number=1,
                )
            ],
            tables=[],
            language="en",
            page_count=1,
            processing_time_ms=duration_ms,
            metadata={"width": width, "height": height, "format": img.format},
        )


class ProductionCloudOCRProvider(BaseOCRProvider):
    """Production interface for Enterprise Cloud OCR (AWS Textract / Google Cloud Vision / Azure Document Intelligence)."""

    def __init__(self, cloud_provider: str = "aws_textract"):
        self.cloud_provider = cloud_provider

    async def extract(self, file_bytes: bytes, mime_type: str, **kwargs) -> OCRResult:
        # In production with cloud credentials, this calls the respective SDK
        raise NotImplementedError(
            f"Production cloud OCR provider '{self.cloud_provider}' requires configured cloud credentials."
        )
