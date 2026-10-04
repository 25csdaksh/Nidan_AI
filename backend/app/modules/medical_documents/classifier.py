import io
import re
from typing import Optional, Tuple
from pypdf import PdfReader
from app.modules.medical_documents.models import DocumentTypeEnum


class DocumentClassifier:
    """
    Deterministic clinical document classifier.
    Uses safe rule-based keyword density and structural heuristics without probabilistic LLMs.
    """

    BLOOD_REPORT_KEYWORDS = {
        "hematology", "hemoglobin", "complete blood count", "cbc", "lipid profile",
        "wbc", "platelet", "serum creatinine", "liver function", "fasting glucose",
        "kft", "lft", "hba1c", "blood test", "pathology report", "reference interval",
        "ref range", "triglycerides", "bilirubin", "erythrocyte", "neutrophils",
        "lymphocytes", "serum potassium", "serum sodium", "blood urea",
    }

    PRESCRIPTION_KEYWORDS = {
        "rx", "tab.", "cap.", "syrup", "dosage", "frequency", "once daily",
        "bid", "tid", "qid", "take after meals", "prescribed by", "doctor prescription",
        "mg/day", "medication", "sig:", "disp:", "pharmacist", "dr.", "oral",
    }

    XRAY_KEYWORDS = {
        "chest pa view", "x-ray", "xray", "radiograph", "lungs clear",
        "cardiomegaly", "ribs", "bone fracture", "no focal consolidation",
        "apical view", "radiology report", "costophrenic angles", "mediastinum",
    }

    SONOGRAPHY_KEYWORDS = {
        "sonography", "ultrasound", "usg", "gestational age", "amniotic fluid",
        "bpd", "fl", "echotexture", "urinary bladder", "cholelithiasis",
        "kidneys normal size", "gall bladder", "acoustic shadowing", "pelvic scan",
    }

    @classmethod
    def classify(
        cls,
        file_bytes: bytes,
        mime_type: str,
        original_filename: str,
        manual_override: Optional[str] = None,
    ) -> Tuple[DocumentTypeEnum, float, dict]:
        """
        Classifies medical document modality.
        Returns (DocumentTypeEnum, confidence_score, metadata_details).
        """
        # 1. Respect manual doctor selection if provided
        if manual_override and manual_override.upper() in DocumentTypeEnum.__members__:
            selected = DocumentTypeEnum(manual_override.upper())
            if selected != DocumentTypeEnum.UNKNOWN:
                return selected, 1.0, {"classified_by": "MANUAL_DOCTOR_SELECTION"}

        extracted_text = ""
        has_embedded_text = False
        page_count = 1

        # 2. Extract text if PDF
        if mime_type == "application/pdf":
            try:
                reader = PdfReader(io.BytesIO(file_bytes))
                page_count = len(reader.pages)
                for page in reader.pages[:10]:  # Inspect first 10 pages max
                    text = page.extract_text()
                    if text:
                        extracted_text += " " + text.lower()
                if extracted_text.strip():
                    has_embedded_text = True
            except Exception:
                pass

        # 3. Analyze extracted text density
        if has_embedded_text:
            blood_score = sum(1 for kw in cls.BLOOD_REPORT_KEYWORDS if kw in extracted_text)
            rx_score = sum(1 for kw in cls.PRESCRIPTION_KEYWORDS if kw in extracted_text)
            xray_score = sum(1 for kw in cls.XRAY_KEYWORDS if kw in extracted_text)
            usg_score = sum(1 for kw in cls.SONOGRAPHY_KEYWORDS if kw in extracted_text)

            scores = [
                (DocumentTypeEnum.BLOOD_REPORT, blood_score),
                (DocumentTypeEnum.PRESCRIPTION, rx_score),
                (DocumentTypeEnum.XRAY, xray_score),
                (DocumentTypeEnum.SONOGRAPHY, usg_score),
            ]
            scores.sort(key=lambda x: x[1], reverse=True)
            top_type, top_score = scores[0]

            if top_score >= 2:
                confidence = min(0.95, 0.5 + (top_score * 0.1))
                return top_type, confidence, {
                    "classified_by": "PDF_TEXT_CONTENT_ANALYSIS",
                    "matched_signal_score": top_score,
                    "has_embedded_text": True,
                    "page_count": page_count,
                }

        # 4. Filename keyword fallback heuristic
        fn_lower = original_filename.lower()
        if any(w in fn_lower for w in ["blood", "cbc", "lipid", "lft", "kft", "lab", "hematology"]):
            return DocumentTypeEnum.BLOOD_REPORT, 0.70, {"classified_by": "FILENAME_SIGNAL", "has_embedded_text": has_embedded_text}
        if any(w in fn_lower for w in ["rx", "prescription", "meds", "medicines"]):
            return DocumentTypeEnum.PRESCRIPTION, 0.70, {"classified_by": "FILENAME_SIGNAL", "has_embedded_text": has_embedded_text}
        if any(w in fn_lower for w in ["xray", "x-ray", "cxr", "radiograph"]):
            return DocumentTypeEnum.XRAY, 0.70, {"classified_by": "FILENAME_SIGNAL", "has_embedded_text": has_embedded_text}
        if any(w in fn_lower for w in ["usg", "ultrasound", "sonography", "sono"]):
            return DocumentTypeEnum.SONOGRAPHY, 0.70, {"classified_by": "FILENAME_SIGNAL", "has_embedded_text": has_embedded_text}

        # 5. Safe Fallback: UNKNOWN (Strict non-hallucination policy)
        return DocumentTypeEnum.UNKNOWN, 0.0, {
            "classified_by": "UNDETERMINED_SAFE_FALLBACK",
            "has_embedded_text": has_embedded_text,
            "page_count": page_count,
        }
