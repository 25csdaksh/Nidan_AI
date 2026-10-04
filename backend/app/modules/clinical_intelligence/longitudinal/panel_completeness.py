from typing import Dict, List, Set
from pydantic import BaseModel, Field


class PanelCompletenessResult(BaseModel):
    panel_name: str
    total_expected: int
    present_count: int
    missing_count: int
    is_complete: bool
    present_analytes: List[str] = Field(default_factory=list)
    missing_analytes: List[str] = Field(default_factory=list)
    advisory_message: str


STANDARD_PANEL_DEFINITIONS: Dict[str, List[str]] = {
    "Complete Blood Count (CBC)": [
        "Hemoglobin", "RBC", "WBC", "Platelets", "MCV", "MCH", "MCHC", "Hematocrit"
    ],
    "Renal Function Panel (KFT)": [
        "Serum Creatinine", "BUN", "eGFR", "Uric Acid"
    ],
    "Liver Function Panel (LFT)": [
        "ALT", "AST", "Total Bilirubin", "Alkaline Phosphatase", "Total Protein", "Albumin"
    ],
    "Lipid Profile": [
        "Total Cholesterol", "HDL Cholesterol", "LDL Cholesterol", "Triglycerides"
    ],
    "Thyroid Panel": [
        "TSH", "Free T3", "Free T4"
    ],
    "Iron Metabolism Panel": [
        "Serum Iron", "Ferritin", "TIBC"
    ],
    "Glycemic Control Panel": [
        "Fasting Blood Glucose", "HbA1c"
    ],
}


class PanelCompletenessAnalyzer:
    @classmethod
    def evaluate_panels(cls, observed_canonical_names: List[str]) -> List[PanelCompletenessResult]:
        normalized_observed: Set[str] = {name.strip().lower() for name in observed_canonical_names}
        results: List[PanelCompletenessResult] = []

        for panel_name, expected_analytes in STANDARD_PANEL_DEFINITIONS.items():
            expected_map = {name.strip().lower(): name for name in expected_analytes}
            present = [expected_map[k] for k in expected_map if k in normalized_observed]
            missing = [expected_map[k] for k in expected_map if k not in normalized_observed]

            if not present:
                continue  # Panel not requested or present

            is_complete = len(missing) == 0
            if is_complete:
                advisory = f"{panel_name} is complete ({len(present)}/{len(expected_analytes)} markers)."
            else:
                advisory = f"Partial {panel_name} ({len(present)} of {len(expected_analytes)} markers observed: {', '.join(present)}). Missing markers: {', '.join(missing)}. Unmeasured markers must not be assumed normal."

            results.append(
                PanelCompletenessResult(
                    panel_name=panel_name,
                    total_expected=len(expected_analytes),
                    present_count=len(present),
                    missing_count=len(missing),
                    is_complete=is_complete,
                    present_analytes=present,
                    missing_analytes=missing,
                    advisory_message=advisory,
                )
            )

        return results

    @classmethod
    def analyze_panel_completeness(cls, observations_or_names) -> List[PanelCompletenessResult]:
        if not observations_or_names:
            return []
        names = []
        for item in observations_or_names:
            if isinstance(item, str):
                names.append(item)
            elif hasattr(item, "canonical_name") and item.canonical_name:
                names.append(item.canonical_name)
            elif hasattr(item, "analyte") and item.analyte:
                names.append(item.analyte)
        return cls.evaluate_panels(names)


