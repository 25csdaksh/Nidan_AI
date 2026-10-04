from typing import Dict, Optional
from pydantic import BaseModel


class AnalyteTrendRule(BaseModel):
    analyte: str
    canonical_name: str
    favorable_direction: str  # HIGHER, LOWER, WITHIN_RANGE
    neutral_delta_abs: float = 0.1
    neutral_delta_pct: float = 3.0  # 3% threshold
    minimum_observations: int = 2
    rule_version: str = "1.0.0"
    source: str = "Evidence-Based Laboratory Medicine Trend Consensus"


ANALYTE_TREND_RULES_CONFIG: Dict[str, AnalyteTrendRule] = {
    "hemoglobin": AnalyteTrendRule(
        analyte="Hemoglobin",
        canonical_name="Hemoglobin",
        favorable_direction="WITHIN_RANGE",
        neutral_delta_abs=0.2,
        neutral_delta_pct=2.0,
    ),
    "serum creatinine": AnalyteTrendRule(
        analyte="Serum Creatinine",
        canonical_name="Serum Creatinine",
        favorable_direction="LOWER",
        neutral_delta_abs=0.1,
        neutral_delta_pct=5.0,
    ),
    "egfr": AnalyteTrendRule(
        analyte="eGFR",
        canonical_name="eGFR",
        favorable_direction="HIGHER",
        neutral_delta_abs=3.0,
        neutral_delta_pct=5.0,
    ),
    "fasting blood glucose": AnalyteTrendRule(
        analyte="Fasting Blood Glucose",
        canonical_name="Fasting Blood Glucose",
        favorable_direction="LOWER",
        neutral_delta_abs=5.0,
        neutral_delta_pct=4.0,
    ),
    "hba1c": AnalyteTrendRule(
        analyte="HbA1c",
        canonical_name="HbA1c",
        favorable_direction="LOWER",
        neutral_delta_abs=0.2,
        neutral_delta_pct=3.0,
    ),
    "vitamin d, 25-oh": AnalyteTrendRule(
        analyte="Vitamin D, 25-OH",
        canonical_name="Vitamin D, 25-OH",
        favorable_direction="HIGHER",
        neutral_delta_abs=2.0,
        neutral_delta_pct=5.0,
    ),
    "vitamin b12": AnalyteTrendRule(
        analyte="Vitamin B12",
        canonical_name="Vitamin B12",
        favorable_direction="HIGHER",
        neutral_delta_abs=15.0,
        neutral_delta_pct=5.0,
    ),
    "ferritin": AnalyteTrendRule(
        analyte="Ferritin",
        canonical_name="Ferritin",
        favorable_direction="WITHIN_RANGE",
        neutral_delta_abs=5.0,
        neutral_delta_pct=5.0,
    ),
    "alt": AnalyteTrendRule(
        analyte="ALT",
        canonical_name="ALT",
        favorable_direction="LOWER",
        neutral_delta_abs=4.0,
        neutral_delta_pct=6.0,
    ),
    "ast": AnalyteTrendRule(
        analyte="AST",
        canonical_name="AST",
        favorable_direction="LOWER",
        neutral_delta_abs=4.0,
        neutral_delta_pct=6.0,
    ),
    "total bilirubin": AnalyteTrendRule(
        analyte="Total Bilirubin",
        canonical_name="Total Bilirubin",
        favorable_direction="LOWER",
        neutral_delta_abs=0.2,
        neutral_delta_pct=8.0,
    ),
    "tsh": AnalyteTrendRule(
        analyte="TSH",
        canonical_name="TSH",
        favorable_direction="WITHIN_RANGE",
        neutral_delta_abs=0.3,
        neutral_delta_pct=6.0,
    ),
    "platelets": AnalyteTrendRule(
        analyte="Platelets",
        canonical_name="Platelets",
        favorable_direction="WITHIN_RANGE",
        neutral_delta_abs=15.0,
        neutral_delta_pct=5.0,
    ),
    "wbc": AnalyteTrendRule(
        analyte="WBC",
        canonical_name="WBC",
        favorable_direction="WITHIN_RANGE",
        neutral_delta_abs=0.5,
        neutral_delta_pct=5.0,
    ),
}


def get_trend_rule(canonical_name: str) -> AnalyteTrendRule:
    key = canonical_name.strip().lower()
    if key in ANALYTE_TREND_RULES_CONFIG:
        return ANALYTE_TREND_RULES_CONFIG[key]
    return AnalyteTrendRule(
        analyte=canonical_name,
        canonical_name=canonical_name,
        favorable_direction="WITHIN_RANGE",
        neutral_delta_abs=0.1,
        neutral_delta_pct=3.0,
    )
