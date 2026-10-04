"""Medical Entity Extractor for Clinical Laboratory Documents.

Transforms raw OCR text lines and blocks into structured, canonical clinical entities
with strict provenance, unit normalization, reference range extraction, and confidence scoring.
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.modules.medical_documents.extraction.base import BoundingBox, OCRResult, OCRTextBlock
from app.modules.medical_documents.extraction.confidence import ConfidenceCalculator
from app.modules.medical_documents.extraction.normalizer import (
    evaluate_technical_status,
    normalize_unit,
    parse_numeric_value,
    parse_reference_range,
)
from app.modules.medical_documents.extraction.vocabulary import (
    ANALYTE_CATALOG,
    SYNONYM_LOOKUP,
    get_canonical_analyte,
)


class ExtractedEntity(BaseModel):
    entity_type: str = "LAB_ANALYTE"
    raw_name: str
    canonical_name: str
    value_text: str
    numeric_value: Optional[float] = None
    original_unit: Optional[str] = None
    normalized_unit: Optional[str] = None
    reference_range_text: Optional[str] = None
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    technical_status: str = "UNKNOWN"
    confidence: float = 1.0
    page_number: int = 1
    bounding_box: Optional[Dict[str, Any]] = None
    source_text: str


class MedicalEntityExtractor:
    """Deterministic extractor for laboratory test results from OCR results."""

    def __init__(self):
        # Build regex patterns sorted by longest synonym first to avoid partial prefix collisions
        all_synonyms = sorted(SYNONYM_LOOKUP.keys(), key=len, reverse=True)
        # Escape special regex characters in synonyms
        escaped_syns = [re.escape(syn) for syn in all_synonyms]
        self.analyte_regex = re.compile(
            r"\b(" + "|".join(escaped_syns) + r")\b",
            re.IGNORECASE,
        )

    def extract_entities(self, ocr_result: OCRResult) -> List[ExtractedEntity]:
        entities: List[ExtractedEntity] = []
        seen_analytes = set()

        # Iterate through text blocks
        for block in ocr_result.blocks:
            line_text = block.text.strip()
            if not line_text:
                continue

            # Look for analyte name in the line
            matches = list(self.analyte_regex.finditer(line_text))
            if not matches:
                continue

            for match in matches:
                matched_raw_name = match.group(1)
                canonical_name = get_canonical_analyte(matched_raw_name)
                if not canonical_name:
                    continue

                # Deduplication per document page/run if identical value already extracted
                analyte_key = f"{canonical_name}_{block.page}"
                if analyte_key in seen_analytes:
                    continue

                # Extract remainder of line following the analyte name
                after_match_text = line_text[match.end():].strip()
                # Clean leading punctuation like ':', '-', '='
                after_match_text = re.sub(r"^[:\-=–—\s]+", "", after_match_text).strip()

                # Extract numeric value
                num_val, val_text = parse_numeric_value(after_match_text)
                if num_val is None:
                    # Maybe the number is before or in a multi-column format
                    # Try finding any number in the line
                    num_val, val_text = parse_numeric_value(line_text)
                    if num_val is None:
                        continue

                # Extract unit and reference range candidates
                analyte_def = ANALYTE_CATALOG.get(canonical_name)
                detected_unit: Optional[str] = None
                normalized_unit_str: Optional[str] = None
                is_standard_unit = False

                # Look for common units in after_match_text
                if analyte_def and analyte_def.common_units:
                    for u in analyte_def.common_units:
                        u_pattern = r"\b" + re.escape(u) + r"\b"
                        if re.search(u_pattern, after_match_text, re.IGNORECASE):
                            detected_unit = u
                            normalized_unit_str, is_standard_unit = normalize_unit(u)
                            break

                if not detected_unit:
                    # Generic unit search
                    unit_match = re.search(r"([a-zA-Z/%^0-9\.\-]+(?:/[a-zA-Z0-9\.\^]+)?)", after_match_text)
                    if unit_match:
                        cand_unit = unit_match.group(1)
                        norm_u, is_std = normalize_unit(cand_unit)
                        if is_std:
                            detected_unit = cand_unit
                            normalized_unit_str = norm_u
                            is_standard_unit = True

                if not normalized_unit_str and analyte_def:
                    normalized_unit_str = analyte_def.default_unit

                # Extract reference range
                ref_range_cand: Optional[str] = None
                ref_match = re.search(
                    r"(?:ref(?:erence)?\s*(?:range)?[:\s]*|normal[:\s]*|interval[:\s]*|\(|\[)?(\d+(?:\.\d+)?\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?|[<>]=?\s*\d+(?:\.\d+)?)(?:\)|\])?",
                    after_match_text,
                    re.IGNORECASE,
                )
                if ref_match:
                    ref_range_cand = ref_match.group(1)


                parsed_range = parse_reference_range(ref_range_cand)
                ref_min = parsed_range.min_value if parsed_range else None
                ref_max = parsed_range.max_value if parsed_range else None
                ref_text = parsed_range.raw_text if parsed_range else None

                # Evaluate technical range status
                tech_status = evaluate_technical_status(num_val, ref_min, ref_max)

                # Compute extraction confidence
                confidence = ConfidenceCalculator.calculate(
                    ocr_confidence=block.confidence,
                    is_exact_synonym_match=True,
                    has_numeric_value=num_val is not None,
                    has_valid_unit=normalized_unit_str is not None,
                    has_reference_range=parsed_range is not None and (ref_min is not None or ref_max is not None),
                )

                bbox_dict = None
                if block.bounding_box:
                    bbox_dict = block.bounding_box.model_dump()


                entity = ExtractedEntity(
                    entity_type="LAB_ANALYTE",
                    raw_name=matched_raw_name,
                    canonical_name=canonical_name,
                    value_text=str(num_val) if num_val is not None else val_text,
                    numeric_value=num_val,
                    original_unit=detected_unit,
                    normalized_unit=normalized_unit_str,
                    reference_range_text=ref_text,
                    reference_min=ref_min,
                    reference_max=ref_max,
                    technical_status=tech_status,
                    confidence=confidence,
                    page_number=block.page,
                    bounding_box=bbox_dict,
                    source_text=line_text,
                )

                entities.append(entity)
                seen_analytes.add(analyte_key)

        return entities
