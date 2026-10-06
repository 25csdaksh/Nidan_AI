import re
from typing import List, Set, Tuple
from app.modules.doctor_copilot.schemas import QueryType

# Prohibited decision keywords
PROHIBITED_PATTERNS = [
    r"\b(prescribe|prescribing|prescription for|give patient|give rx)\b",
    r"\b(recommend medication|recommend drug|recommend antibiotic)\b",
    r"\b(diagnose|diagnosis of|what disease does|does patient have (cancer|diabetes|anemia|infection|covid))\b",
    r"\b(what is the (prognosis|life expectancy|survival rate))\b",
    r"\b(start (medication|drug|therapy|insulin|metformin|antibiotic)|stop (medication|drug|therapy))\b",
    r"\b(change dose|increase dose|decrease dose|titrate|dosage recommendation)\b",
    r"\b(treatment plan|cure|how to treat)\b",
]

def classify_query(query: str) -> QueryType:
    """
    Deterministically classifies a clinician query into supported categories or prohibited decisions.
    """
    q = query.lower().strip()

    # 1. Prohibited clinical decisions check first
    for pat in PROHIBITED_PATTERNS:
        if re.search(pat, q):
            # Check if it's merely asking about safety findings vs demanding a prescription
            if not ("safety" in q or "interaction" in q or "finding" in q or "summarize" in q or "show" in q):
                return QueryType.PROHIBITED_CLINICAL_DECISION

    # 2. General medical knowledge check (e.g. "what does HbA1c measure", "what is creatinine", "normal range for WBC")
    if re.search(r"^(what is|what does|explain|definition of|how does)\s+[a-z0-9\s]+(measure|mean|function|indicate|do)\??$", q):
        if not ("this patient" in q or "my patient" in q or "current" in q or "recent" in q):
            return QueryType.GENERAL_MEDICAL_KNOWLEDGE

    # 3. Patient Clinical Summary
    if re.search(r"\b(summarize|summary|overview)\b.*\b(patient|clinical|status|record|history|consultation)\b", q) or re.search(r"\b(patient|clinical)\b.*\b(summary|overview)\b", q):
        return QueryType.PATIENT_SUMMARY
    if any(k in q for k in ["summarize patient", "patient summary", "clinical summary", "before consultation", "overall summary", "overview", "summarize this patient"]):
        return QueryType.PATIENT_SUMMARY


    # 4. Lab Comparison
    if any(k in q for k in ["compare", "comparison", "what changed", "difference between", "latest two", "previous report"]):
        return QueryType.LAB_COMPARISON

    # 5. Longitudinal Trends
    if any(k in q for k in ["trend", "trajectory", "over time", "longitudinal", "history of", "fluctuat", "persistent"]):
        return QueryType.TREND_QUERY

    # 6. Abnormalities
    if any(k in q for k in ["abnormal", "critical", "out of range", "high or low", "deficiency", "flagged"]):
        return QueryType.ABNORMALITY_QUERY

    # 7. Medication Safety & Interactions
    if any(k in q for k in ["interaction", "allergy", "duplicate", "safety finding", "safety signal", "contraindication", "safe to take"]):
        return QueryType.MEDICATION_SAFETY_QUERY

    # 8. Medications & Prescriptions
    if any(k in q for k in ["prescription", "prescriptions", "rx record", "prescriber"]):
        return QueryType.PRESCRIPTION_QUERY
    if any(k in q for k in ["medication", "medications", "drugs", "current meds", "taking"]):
        return QueryType.MEDICATION_QUERY

    # 9. Lab Summary
    if any(k in q for k in ["lab", "laboratory", "blood report", "cbc", "kft", "lft", "lipid", "thyroid", "test result", "hemoglobin", "creatinine", "glucose", "hba1c"]):
        return QueryType.LAB_SUMMARY

    # 10. Data quality & Missing Info
    if any(k in q for k in ["missing", "data quality", "incomplete", "what is not available", "unverified"]):
        return QueryType.DATA_QUALITY_QUERY

    # 11. Evidence & Provenance
    if any(k in q for k in ["evidence", "provenance", "source", "why did nidan", "where is this from"]):
        return QueryType.EVIDENCE_QUERY

    # 12. Imaging Studies & Findings (Phase 7)
    if any(k in q for k in ["compare x-ray", "compare imaging", "contrast x-ray", "imaging comparison", "difference between x-ray"]):
        return QueryType.IMAGING_COMPARISON
    if any(k in q for k in ["x-ray", "xray", "chest x-ray", "chest radiograph", "radiograph", "radiology", "imaging", "cardiomegaly", "effusion", "atelectasis", "consolidation", "pneumothorax"]):
        return QueryType.IMAGING_QUERY

    # 13. Documents
    if any(k in q for k in ["document", "uploaded", "file", "report pdf", "scanned"]):
        return QueryType.DOCUMENT_QUERY

    # 14. Timeline
    if any(k in q for k in ["timeline", "chronology", "visit history", "encounters"]):
        return QueryType.TIMELINE_QUERY

    return QueryType.GENERAL_QUERY


def extract_query_entities(query: str) -> Set[str]:
    """
    Extracts clinical entity keywords (analyte names, drug names, imaging finding terms) mentioned in the query.
    """
    known_entities = {
        "hemoglobin", "hb", "hgb", "creatinine", "glucose", "hba1c", "potassium",
        "sodium", "calcium", "platelet", "platelets", "wbc", "rbc", "alt", "ast",
        "bilirubin", "cholesterol", "triglycerides", "tsh", "vitamin d", "vitamin b12",
        "ferritin", "iron", "urea", "bun", "egfr", "metformin", "lisinopril", "atorvastatin",
        "aspirin", "warfarin", "amoxicillin", "spironolactone", "omeprazole", "paracetamol",
        "azithromycin", "ciprofloxacin", "x-ray", "xray", "chest x-ray", "cardiomegaly",
        "pleural effusion", "effusion", "atelectasis", "consolidation", "edema",
        "pneumothorax", "infiltration", "nodule", "fibrosis", "pleural thickening",
    }
    q = query.lower()
    found: Set[str] = set()
    for ent in known_entities:
        if re.search(rf"\b{re.escape(ent)}\b", q):
            found.add(ent)
    return found
