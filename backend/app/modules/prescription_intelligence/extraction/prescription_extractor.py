"""Prescription Document Extractor Orchestrator for NIDAN AI Phase 5.

Processes OCR results from medical documents to produce structured:
- Prescription metadata (Prescriber, Date, Status, Confidence)
- Extracted medication items
"""

import re
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field

from app.modules.medical_documents.extraction.base import OCRResult
from app.modules.prescription_intelligence.extraction.medication_parser import (
    MedicationParser,
    ParsedMedicationItem,
)


class ExtractedPrescription(BaseModel):
    prescriber_name: Optional[str] = None
    prescription_date: Optional[datetime] = None
    source_confidence: float = 1.0
    status: str = "EXTRACTED"  # EXTRACTED or REVIEW_REQUIRED
    medications: List[ParsedMedicationItem] = Field(default_factory=list)
    raw_text: str = ""
    processing_time_ms: int = 0


class PrescriptionExtractor:
    """Orchestrates structured prescription extraction from OCR output."""

    @classmethod
    def extract_prescriber(cls, text: str) -> Optional[str]:
        """Extracts doctor/prescriber name if explicitly documented."""
        if not text:
            return None

        # Matches 'Dr. John Doe', 'Doctor: Jane Smith', 'Prescriber: Dr. Alex'
        pattern = r"\b(?:dr\.|doctor\s*:?|prescriber\s*:?)\s*([A-Z][a-zA-Z\.\s]{2,30})\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            # Clean trailing noise
            candidate = re.split(r"[\n,\-–]", candidate)[0].strip()
            if len(candidate) > 2:
                return f"Dr. {candidate}" if not candidate.lower().startswith("dr.") else candidate

        return None

    @classmethod
    def extract_prescription_date(cls, text: str) -> Optional[datetime]:
        """Extracts prescription date if explicitly present."""
        if not text:
            return None

        patterns = [
            r"\b(?:date|rx\s+date|prescribed\s+on)\s*:?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b",
            r"\b(?:date|rx\s+date|prescribed\s+on)\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b",
            r"\b(\d{4}-\d{2}-\d{2})\b",
            r"\b(\d{1,2}/\d{1,2}/\d{4})\b",
        ]

        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        return dt.replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue

        return None

    @classmethod
    def extract(cls, ocr_result: OCRResult) -> ExtractedPrescription:
        """Extracts all prescription metadata and medications from an OCR result."""
        raw_text = ocr_result.raw_text or ""
        prescriber = cls.extract_prescriber(raw_text)
        presc_date = cls.extract_prescription_date(raw_text)

        extracted_meds: List[ParsedMedicationItem] = []
        seen_signatures = set()

        # 1. Process block by block
        if ocr_result.blocks:
            for block in ocr_result.blocks:
                if isinstance(block, dict):
                    b_text = block.get("text", "")
                    p_num = block.get("page", 1)
                    b_box = block.get("bounding_box")
                else:
                    b_text = getattr(block, "text", "")
                    p_num = getattr(block, "page", 1)
                    b_box = getattr(block, "bounding_box", None)
                    if hasattr(b_box, "model_dump"):
                        b_box = b_box.model_dump()
                items = MedicationParser.parse_text_lines(b_text, page_number=p_num)
                for item in items:
                    if b_box:
                        item.bounding_box = b_box
                    sig = (item.canonical_medication_name, item.strength_value, item.strength_unit, item.frequency_code)
                    if sig not in seen_signatures:
                        seen_signatures.add(sig)
                        extracted_meds.append(item)

        # 2. Fallback to full raw text if blocks yielded nothing
        if not extracted_meds and raw_text:
            items = MedicationParser.parse_text_lines(raw_text, page_number=1)
            for item in items:
                sig = (item.canonical_medication_name, item.strength_value, item.strength_unit, item.frequency_code)
                if sig not in seen_signatures:
                    seen_signatures.add(sig)
                    extracted_meds.append(item)

        # 3. Determine status and overall source confidence
        final_status = "EXTRACTED"
        if not extracted_meds:
            final_status = "REVIEW_REQUIRED"
            source_conf = 0.50
        else:
            avg_conf = sum(m.confidence for m in extracted_meds) / len(extracted_meds)
            source_conf = round(avg_conf, 2)
            if any(m.confidence < 0.80 or m.canonical_medication_name == "UNKNOWN" for m in extracted_meds):
                final_status = "REVIEW_REQUIRED"

        return ExtractedPrescription(
            prescriber_name=prescriber,
            prescription_date=presc_date,
            source_confidence=source_conf,
            status=final_status,
            medications=extracted_meds,
            raw_text=raw_text,
            processing_time_ms=ocr_result.processing_time_ms,
        )
