"""Medication Line and Block Parser for Prescription Intelligence.

Splits OCR blocks / text lines and extracts structured medication fields:
- raw_medication_name, canonical_name, generic_name, brand_name
- strength_value, strength_unit
- dosage_form
- route
- frequency_code, frequency_text
- dose_quantity
- duration_value, duration_unit
- instruction_text
- is_prn
- confidence
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field

from app.modules.prescription_intelligence.extraction.confidence import PrescriptionConfidenceScorer
from app.modules.prescription_intelligence.extraction.instruction_parser import InstructionParser
from app.modules.prescription_intelligence.medication.dosage_parser import DosageParser
from app.modules.prescription_intelligence.medication.duration_parser import DurationParser
from app.modules.prescription_intelligence.medication.frequency_parser import FrequencyParser
from app.modules.prescription_intelligence.medication.normalization import MedicationNormalizer
from app.modules.prescription_intelligence.medication.route_parser import RouteParser
from app.modules.prescription_intelligence.medication.vocabulary import (
    DOSAGE_FORMS,
    MEDICATION_CATALOG,
)


class ParsedMedicationItem(BaseModel):
    raw_medication_name: str
    canonical_medication_name: str
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None
    strength_value: Optional[float] = None
    strength_unit: Optional[str] = None
    dosage_form: Optional[str] = None
    route: Optional[str] = None
    frequency_code: Optional[str] = None
    frequency_text: Optional[str] = None
    dose_quantity: Optional[str] = None
    duration_value: Optional[int] = None
    duration_unit: Optional[str] = None
    instruction_text: Optional[str] = None
    is_prn: bool = False
    confidence: float = 1.0
    source_text: str
    page_number: int = 1
    bounding_box: Optional[dict] = None


class MedicationParser:
    """Deterministic parser that extracts medication entries from prescription text lines."""

    # Keywords that suggest a line is part of a prescription medication entry
    PRESCRIPTION_INDICATORS = {
        "tab", "cap", "inj", "syp", "syrup", "capsule", "tablet", "rx",
        "mg", "mcg", "gm", "ml", "iu", "od", "bd", "bid", "tid", "qid", "prn",
        "sos", "daily", "days", "po", "oral",
    }

    @classmethod
    def is_likely_medication_line(cls, line: str) -> bool:
        """Determines if a text line is likely a prescription medication."""
        line_clean = line.strip().lower()
        if not line_clean or len(line_clean) < 3:
            return False

        # Exclude header/footer noise
        if any(h in line_clean for h in ["clinic", "hospital", "doctor:", "dr.", "patient name", "date:", "age/sex", "signature", "address", "phone", "investigation"]):
            # If line also has Rx or tab/cap it might be a split line, but header lines usually start with doctor/patient
            if re.match(r"^(?:dr\.|patient\s+name|date\s*:|age\s*:|hospital|clinic|tel\s*:)", line_clean):
                return False

        # Check if line contains known drug name or alias
        for data in MEDICATION_CATALOG.values():
            for alias in data.get("aliases", set()):
                if re.search(rf"\b{re.escape(alias)}\b", line_clean):
                    return True

        # Check if line contains strength + frequency or dosage form + strength
        has_strength = bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|iu|%)\b", line_clean))
        has_form = any(re.search(rf"\b{re.escape(f)}\b", line_clean) for f in DOSAGE_FORMS)
        has_freq = bool(re.search(r"\b(?:od|bd|bid|tid|qid|q8h|q12h|prn|sos|daily|once\s+daily|twice\s+daily)\b", line_clean))

        if (has_strength and has_freq) or (has_form and has_strength) or (has_form and has_freq):
            return True

        return False

    @classmethod
    def parse_line(cls, line: str, page_number: int = 1, bounding_box: Optional[dict] = None) -> Optional[ParsedMedicationItem]:
        """Parses a single line into a structured ParsedMedicationItem."""
        clean_line = line.strip()
        if not clean_line:
            return None

        # 1. Extract dosage form
        dosage_form = DosageParser.parse_dosage_form(clean_line)

        # 2. Extract strength
        strength_val, strength_unit = DosageParser.parse_strength(clean_line)

        # 3. Extract route
        route = RouteParser.parse_route(clean_line)

        # 4. Extract frequency and PRN
        freq_code, freq_text, is_prn = FrequencyParser.parse_frequency(clean_line)

        # 5. Extract dose quantity
        dose_quantity = DosageParser.parse_dose_quantity(clean_line)

        # 6. Extract duration
        duration_val, duration_unit = DurationParser.parse_duration(clean_line)

        # 7. Extract instructions
        instruction_text = InstructionParser.parse_instructions(clean_line)

        # 8. Extract raw medication name
        # Strategy: strip numbers, bullets, 'Rx', dosage form keywords, strength, frequency, duration
        raw_med_name = clean_line
        # Remove leading Rx / number
        raw_med_name = re.sub(r"^(?:rx[\s:\.\-]*|\d+[\.\)\-]\s*|[\*\-\•]\s*)", "", raw_med_name, flags=re.IGNORECASE)
        # Remove leading dosage form
        for form in sorted(DOSAGE_FORMS, key=len, reverse=True):
            raw_med_name = re.sub(rf"^{re.escape(form)}\.?\s+", "", raw_med_name, flags=re.IGNORECASE)

        # Take first 1-3 words before strength/frequency/instructions as the raw drug name
        tokens = raw_med_name.split()
        candidate_words = []
        for t in tokens:
            t_low = t.lower().strip(" ,.-:;")
            if not t_low:
                continue
            # Stop if token looks like a strength, frequency, duration, or route
            if re.match(r"^\d+(?:\.\d+)?(?:mg|g|mcg|ml|iu|%)?$", t_low) or t_low in {"od", "bd", "bid", "tid", "qid", "prn", "sos", "oral", "po", "tab", "cap", "x", "for", "pc", "ac"}:
                break
            candidate_words.append(t)
            if len(candidate_words) >= 3:
                break

        if candidate_words:
            raw_name_extracted = " ".join(candidate_words).strip(" ,.-:;")
        else:
            raw_name_extracted = clean_line[:40].strip()

        # 9. Normalize medication
        canonical_name, generic_name, brand_name, norm_conf = MedicationNormalizer.normalize(raw_name_extracted)

        # If normalization gave UNKNOWN, check if full line contains a catalog medication
        if canonical_name == "UNKNOWN":
            for cat_name, cat_data in MEDICATION_CATALOG.items():
                for alias in cat_data.get("aliases", set()):
                    if re.search(rf"\b{re.escape(alias)}\b", clean_line.lower()):
                        canonical_name = cat_name
                        generic_name = cat_data.get("generic")
                        raw_name_extracted = alias.capitalize()
                        norm_conf = 0.90
                        break
                if canonical_name != "UNKNOWN":
                    break

        # 10. Calculate overall confidence
        confidence = PrescriptionConfidenceScorer.calculate_confidence(
            canonical_name=canonical_name,
            norm_confidence=norm_conf,
            strength_val=strength_val,
            strength_unit=strength_unit,
            frequency_code=freq_code,
            dosage_form=dosage_form,
            route=route,
            duration_val=duration_val,
        )

        return ParsedMedicationItem(
            raw_medication_name=raw_name_extracted or clean_line,
            canonical_medication_name=canonical_name,
            generic_name=generic_name,
            brand_name=brand_name,
            strength_value=strength_val,
            strength_unit=strength_unit,
            dosage_form=dosage_form,
            route=route,
            frequency_code=freq_code,
            frequency_text=freq_text,
            dose_quantity=dose_quantity,
            duration_value=duration_val,
            duration_unit=duration_unit,
            instruction_text=instruction_text,
            is_prn=is_prn,
            confidence=confidence,
            source_text=clean_line,
            page_number=page_number,
            bounding_box=bounding_box,
        )

    @classmethod
    def parse_text_lines(cls, text: str, page_number: int = 1) -> List[ParsedMedicationItem]:
        """Parses multiline text and returns list of extracted medications."""
        items: List[ParsedMedicationItem] = []
        if not text:
            return items

        lines = text.splitlines()
        for line in lines:
            line_str = line.strip()
            if cls.is_likely_medication_line(line_str):
                item = cls.parse_line(line_str, page_number=page_number)
                if item:
                    items.append(item)

        return items
