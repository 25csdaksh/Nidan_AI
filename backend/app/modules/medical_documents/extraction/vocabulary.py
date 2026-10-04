"""Controlled clinical analyte dictionary with synonyms and canonical mappings.

No fuzzy guesses on critical medical parameters.
"""

from typing import Dict, List, Optional, Set
from pydantic import BaseModel


class AnalyteDefinition(BaseModel):
    canonical_name: str
    panel: str
    category: str
    synonyms: List[str]
    default_unit: Optional[str] = None
    common_units: List[str] = []


# Controlled clinical analyte catalog
ANALYTE_CATALOG: Dict[str, AnalyteDefinition] = {
    # 1. CBC / Hematology
    "Hemoglobin": AnalyteDefinition(
        canonical_name="Hemoglobin",
        panel="CBC",
        category="Hematology",
        synonyms=["hb", "hgb", "hemoglobin", "haemoglobin", "hemo", "हिमोग्लोबिन", "હિમોગ્લોબિન"],
        default_unit="g/dL",
        common_units=["g/dL", "g/L", "gm/dl", "g%"],
    ),
    "RBC": AnalyteDefinition(
        canonical_name="RBC",
        panel="CBC",
        category="Hematology",
        synonyms=["rbc", "rbc count", "red blood cell", "red blood cells", "erythrocytes", "erythrocyte count"],
        default_unit="10^6/uL",
        common_units=["10^6/uL", "million/uL", "million/cumm", "mil/uL", "x10^12/L"],
    ),
    "WBC": AnalyteDefinition(
        canonical_name="WBC",
        panel="CBC",
        category="Hematology",
        synonyms=["wbc", "wbc count", "white blood cell", "white blood cells", "total leukocyte count", "tlc", "leukocytes"],
        default_unit="10^3/uL",
        common_units=["10^3/uL", "thousand/uL", "/uL", "/cumm", "cells/cu.mm", "cells/cumm", "x10^9/L"],
    ),
    "Platelets": AnalyteDefinition(
        canonical_name="Platelets",
        panel="CBC",
        category="Hematology",
        synonyms=["platelet", "platelets", "platelet count", "thrombocytes", "plt"],
        default_unit="10^3/uL",
        common_units=["10^3/uL", "thousand/uL", "lakhs/cumm", "cells/cumm", "x10^9/L", "/cumm"],
    ),
    "Hematocrit": AnalyteDefinition(
        canonical_name="Hematocrit",
        panel="CBC",
        category="Hematology",
        synonyms=["hematocrit", "haematocrit", "pcv", "packed cell volume", "hct"],
        default_unit="%",
        common_units=["%", "vol%"],
    ),
    "MCV": AnalyteDefinition(
        canonical_name="MCV",
        panel="CBC",
        category="Hematology",
        synonyms=["mcv", "mean corpuscular volume", "mean cell volume"],
        default_unit="fL",
        common_units=["fL", "fl", "cu.microns"],
    ),
    "MCH": AnalyteDefinition(
        canonical_name="MCH",
        panel="CBC",
        category="Hematology",
        synonyms=["mch", "mean corpuscular hemoglobin", "mean cell hemoglobin"],
        default_unit="pg",
        common_units=["pg", "picograms"],
    ),
    "MCHC": AnalyteDefinition(
        canonical_name="MCHC",
        panel="CBC",
        category="Hematology",
        synonyms=["mchc", "mean corpuscular hemoglobin concentration"],
        default_unit="g/dL",
        common_units=["g/dL", "%", "g/L"],
    ),
    "RDW": AnalyteDefinition(
        canonical_name="RDW",
        panel="CBC",
        category="Hematology",
        synonyms=["rdw", "rdw-cv", "rdw-sd", "red cell distribution width"],
        default_unit="%",
        common_units=["%", "fL"],
    ),
    "Neutrophils": AnalyteDefinition(
        canonical_name="Neutrophils",
        panel="CBC",
        category="Hematology",
        synonyms=["neutrophils", "neutrophil", "segs", "segmented neutrophils", "polymorphs"],
        default_unit="%",
        common_units=["%", "/cumm", "/uL"],
    ),
    "Lymphocytes": AnalyteDefinition(
        canonical_name="Lymphocytes",
        panel="CBC",
        category="Hematology",
        synonyms=["lymphocytes", "lymphocyte", "lymphs"],
        default_unit="%",
        common_units=["%", "/cumm", "/uL"],
    ),
    "Monocytes": AnalyteDefinition(
        canonical_name="Monocytes",
        panel="CBC",
        category="Hematology",
        synonyms=["monocytes", "monocyte", "monos"],
        default_unit="%",
        common_units=["%", "/cumm", "/uL"],
    ),
    "Eosinophils": AnalyteDefinition(
        canonical_name="Eosinophils",
        panel="CBC",
        category="Hematology",
        synonyms=["eosinophils", "eosinophil", "eos"],
        default_unit="%",
        common_units=["%", "/cumm", "/uL"],
    ),
    "Basophils": AnalyteDefinition(
        canonical_name="Basophils",
        panel="CBC",
        category="Hematology",
        synonyms=["basophils", "basophil", "baso"],
        default_unit="%",
        common_units=["%", "/cumm", "/uL"],
    ),

    # 2. Glucose Metabolism
    "Glucose": AnalyteDefinition(
        canonical_name="Glucose",
        panel="GLUCOSE",
        category="Metabolism",
        synonyms=["glucose", "blood sugar", "random blood sugar", "rbs", "blood glucose", "ग्लूकोज"],
        default_unit="mg/dL",
        common_units=["mg/dL", "mg%", "mmol/L"],
    ),
    "Fasting Blood Sugar": AnalyteDefinition(
        canonical_name="Fasting Blood Sugar",
        panel="GLUCOSE",
        category="Metabolism",
        synonyms=["fbs", "fasting blood sugar", "fasting blood glucose", "fasting glucose", "fasting plasma glucose", "fpg"],
        default_unit="mg/dL",
        common_units=["mg/dL", "mmol/L"],
    ),
    "Post Prandial Blood Sugar": AnalyteDefinition(
        canonical_name="Post Prandial Blood Sugar",
        panel="GLUCOSE",
        category="Metabolism",
        synonyms=["ppbs", "post prandial blood sugar", "post prandial glucose", "pp blood sugar", "2hr post prandial glucose"],
        default_unit="mg/dL",
        common_units=["mg/dL", "mmol/L"],
    ),
    "HbA1c": AnalyteDefinition(
        canonical_name="HbA1c",
        panel="GLUCOSE",
        category="Metabolism",
        synonyms=["hba1c", "glycated hemoglobin", "glycosylated hemoglobin", "a1c"],
        default_unit="%",
        common_units=["%", "mmol/mol"],
    ),

    # 3. Kidney Function / Renal (KFT)
    "Creatinine": AnalyteDefinition(
        canonical_name="Creatinine",
        panel="RENAL",
        category="Kidney",
        synonyms=["creatinine", "serum creatinine", "creat", "s.creatinine", "क्रेटिनिन"],
        default_unit="mg/dL",
        common_units=["mg/dL", "umol/L", "µmol/L"],
    ),
    "Urea": AnalyteDefinition(
        canonical_name="Urea",
        panel="RENAL",
        category="Kidney",
        synonyms=["urea", "blood urea", "serum urea", "s.urea"],
        default_unit="mg/dL",
        common_units=["mg/dL", "mmol/L"],
    ),
    "BUN": AnalyteDefinition(
        canonical_name="BUN",
        panel="RENAL",
        category="Kidney",
        synonyms=["bun", "blood urea nitrogen"],
        default_unit="mg/dL",
        common_units=["mg/dL", "mmol/L"],
    ),
    "eGFR": AnalyteDefinition(
        canonical_name="eGFR",
        panel="RENAL",
        category="Kidney",
        synonyms=["egfr", "estimated gfr", "glomerular filtration rate", "gfr"],
        default_unit="mL/min/1.73m2",
        common_units=["mL/min/1.73m2", "ml/min/1.73m^2", "ml/min"],
    ),
    "Sodium": AnalyteDefinition(
        canonical_name="Sodium",
        panel="RENAL",
        category="Electrolytes",
        synonyms=["sodium", "serum sodium", "s.sodium", "na", "na+"],
        default_unit="mmol/L",
        common_units=["mmol/L", "mEq/L"],
    ),
    "Potassium": AnalyteDefinition(
        canonical_name="Potassium",
        panel="RENAL",
        category="Electrolytes",
        synonyms=["potassium", "serum potassium", "s.potassium", "k", "k+"],
        default_unit="mmol/L",
        common_units=["mmol/L", "mEq/L"],
    ),
    "Chloride": AnalyteDefinition(
        canonical_name="Chloride",
        panel="RENAL",
        category="Electrolytes",
        synonyms=["chloride", "serum chloride", "s.chloride", "cl", "cl-"],
        default_unit="mmol/L",
        common_units=["mmol/L", "mEq/L"],
    ),

    # 4. Liver Function Tests (LFT)
    "Total Bilirubin": AnalyteDefinition(
        canonical_name="Total Bilirubin",
        panel="LIVER",
        category="Liver",
        synonyms=["total bilirubin", "bilirubin total", "s.bilirubin total", "t.bilirubin", "t bili"],
        default_unit="mg/dL",
        common_units=["mg/dL", "umol/L"],
    ),
    "Direct Bilirubin": AnalyteDefinition(
        canonical_name="Direct Bilirubin",
        panel="LIVER",
        category="Liver",
        synonyms=["direct bilirubin", "conjugated bilirubin", "bilirubin direct", "d.bilirubin"],
        default_unit="mg/dL",
        common_units=["mg/dL", "umol/L"],
    ),
    "AST": AnalyteDefinition(
        canonical_name="AST",
        panel="LIVER",
        category="Liver",
        synonyms=["ast", "sgot", "aspartate transaminase", "aspartate aminotransferase", "serum glutamic oxaloacetic transaminase"],
        default_unit="U/L",
        common_units=["U/L", "IU/L", "u/l"],
    ),
    "ALT": AnalyteDefinition(
        canonical_name="ALT",
        panel="LIVER",
        category="Liver",
        synonyms=["alt", "sgpt", "alanine transaminase", "alanine aminotransferase", "serum glutamic pyruvic transaminase"],
        default_unit="U/L",
        common_units=["U/L", "IU/L", "u/l"],
    ),
    "ALP": AnalyteDefinition(
        canonical_name="ALP",
        panel="LIVER",
        category="Liver",
        synonyms=["alp", "alkaline phosphatase", "alk phos", "s.alkaline phosphatase"],
        default_unit="U/L",
        common_units=["U/L", "IU/L"],
    ),
    "Albumin": AnalyteDefinition(
        canonical_name="Albumin",
        panel="LIVER",
        category="Liver",
        synonyms=["albumin", "serum albumin", "s.albumin"],
        default_unit="g/dL",
        common_units=["g/dL", "g/L"],
    ),
    "Total Protein": AnalyteDefinition(
        canonical_name="Total Protein",
        panel="LIVER",
        category="Liver",
        synonyms=["total protein", "protein total", "serum protein", "s.protein"],
        default_unit="g/dL",
        common_units=["g/dL", "g/L"],
    ),

    # 5. Lipid Profile
    "Total Cholesterol": AnalyteDefinition(
        canonical_name="Total Cholesterol",
        panel="LIPID",
        category="Lipid",
        synonyms=["total cholesterol", "cholesterol total", "serum cholesterol", "s.cholesterol", "cholesterol"],
        default_unit="mg/dL",
        common_units=["mg/dL", "mmol/L"],
    ),
    "LDL": AnalyteDefinition(
        canonical_name="LDL",
        panel="LIPID",
        category="Lipid",
        synonyms=["ldl", "ldl cholesterol", "ldl-c", "low density lipoprotein"],
        default_unit="mg/dL",
        common_units=["mg/dL", "mmol/L"],
    ),
    "HDL": AnalyteDefinition(
        canonical_name="HDL",
        panel="LIPID",
        category="Lipid",
        synonyms=["hdl", "hdl cholesterol", "hdl-c", "high density lipoprotein"],
        default_unit="mg/dL",
        common_units=["mg/dL", "mmol/L"],
    ),
    "Triglycerides": AnalyteDefinition(
        canonical_name="Triglycerides",
        panel="LIPID",
        category="Lipid",
        synonyms=["triglycerides", "serum triglycerides", "tg", "tgl", "triglyceride"],
        default_unit="mg/dL",
        common_units=["mg/dL", "mmol/L"],
    ),
    "VLDL": AnalyteDefinition(
        canonical_name="VLDL",
        panel="LIPID",
        category="Lipid",
        synonyms=["vldl", "vldl cholesterol", "vldl-c", "very low density lipoprotein"],
        default_unit="mg/dL",
        common_units=["mg/dL", "mmol/L"],
    ),

    # 6. Thyroid Function
    "TSH": AnalyteDefinition(
        canonical_name="TSH",
        panel="THYROID",
        category="Thyroid",
        synonyms=["tsh", "thyroid stimulating hormone", "thyrotropin", "s.tsh", "ultra tsh"],
        default_unit="uIU/mL",
        common_units=["uIU/mL", "mIU/L", "µIU/mL", "uU/mL"],
    ),
    "T3": AnalyteDefinition(
        canonical_name="T3",
        panel="THYROID",
        category="Thyroid",
        synonyms=["t3", "triiodothyronine", "total t3"],
        default_unit="ng/dL",
        common_units=["ng/dL", "nmol/L"],
    ),
    "T4": AnalyteDefinition(
        canonical_name="T4",
        panel="THYROID",
        category="Thyroid",
        synonyms=["t4", "thyroxine", "total t4"],
        default_unit="ug/dL",
        common_units=["ug/dL", "µg/dL", "nmol/L"],
    ),
    "Free T3": AnalyteDefinition(
        canonical_name="Free T3",
        panel="THYROID",
        category="Thyroid",
        synonyms=["ft3", "free t3", "free triiodothyronine"],
        default_unit="pg/mL",
        common_units=["pg/mL", "pmol/L"],
    ),
    "Free T4": AnalyteDefinition(
        canonical_name="Free T4",
        panel="THYROID",
        category="Thyroid",
        synonyms=["ft4", "free t4", "free thyroxine"],
        default_unit="ng/dL",
        common_units=["ng/dL", "pmol/L"],
    ),

    # 7. Iron & Ferritin
    "Ferritin": AnalyteDefinition(
        canonical_name="Ferritin",
        panel="IRON",
        category="Iron",
        synonyms=["ferritin", "serum ferritin", "s.ferritin"],
        default_unit="ng/mL",
        common_units=["ng/mL", "ug/L", "µg/L"],
    ),
    "Serum Iron": AnalyteDefinition(
        canonical_name="Serum Iron",
        panel="IRON",
        category="Iron",
        synonyms=["iron", "serum iron", "s.iron", "fe"],
        default_unit="ug/dL",
        common_units=["ug/dL", "µg/dL", "umol/L"],
    ),
    "TIBC": AnalyteDefinition(
        canonical_name="TIBC",
        panel="IRON",
        category="Iron",
        synonyms=["tibc", "total iron binding capacity"],
        default_unit="ug/dL",
        common_units=["ug/dL", "µg/dL", "umol/L"],
    ),
    "Transferrin": AnalyteDefinition(
        canonical_name="Transferrin",
        panel="IRON",
        category="Iron",
        synonyms=["transferrin", "serum transferrin"],
        default_unit="mg/dL",
        common_units=["mg/dL", "g/L"],
    ),
    "Transferrin Saturation": AnalyteDefinition(
        canonical_name="Transferrin Saturation",
        panel="IRON",
        category="Iron",
        synonyms=["transferrin saturation", "tsat", "iron saturation"],
        default_unit="%",
        common_units=["%"],
    ),

    # 8. Vitamins
    "Vitamin B12": AnalyteDefinition(
        canonical_name="Vitamin B12",
        panel="VITAMINS",
        category="Vitamins",
        synonyms=["vitamin b12", "vit b12", "b12", "cyanocobalamin", "cobalamin"],
        default_unit="pg/mL",
        common_units=["pg/mL", "pmol/L"],
    ),
    "Vitamin D": AnalyteDefinition(
        canonical_name="Vitamin D",
        panel="VITAMINS",
        category="Vitamins",
        synonyms=["vitamin d", "vit d", "25-oh vitamin d", "25 hydroxy vitamin d", "vitamin d3", "25(oh)d"],
        default_unit="ng/mL",
        common_units=["ng/mL", "nmol/L"],
    ),
}

# Build fast lookup dictionary: normalized synonym -> canonical name
SYNONYM_LOOKUP: Dict[str, str] = {}
for canonical, definition in ANALYTE_CATALOG.items():
    for syn in definition.synonyms:
        clean_syn = syn.lower().strip()
        SYNONYM_LOOKUP[clean_syn] = canonical


def get_canonical_analyte(raw_name: str) -> Optional[str]:
    """Resolve raw lab analyte name to canonical medical term."""
    if not raw_name:
        return None
    cleaned = raw_name.lower().strip()
    # Direct synonym match
    if cleaned in SYNONYM_LOOKUP:
        return SYNONYM_LOOKUP[cleaned]

    # Clean non-alphanumeric trailing tokens like ':', '-', '.'
    cleaned_stripped = "".join(c for c in cleaned if c.isalnum() or c.isspace()).strip()
    if cleaned_stripped in SYNONYM_LOOKUP:
        return SYNONYM_LOOKUP[cleaned_stripped]

    return None
