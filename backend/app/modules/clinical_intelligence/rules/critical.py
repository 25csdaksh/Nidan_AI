from typing import Any, Dict, List, Optional
from app.modules.clinical_intelligence.rules.base import BaseClinicalRule, RuleEvaluationResult
from app.modules.clinical_intelligence.models import (
    FindingTypeEnum,
    FindingStatusEnum,
    FindingSeverityEnum,
)

# Verified source-backed critical lab alert thresholds
CRITICAL_THRESHOLDS_CONFIG = [
    {
        "canonical_name": "Hemoglobin",
        "unit": "g/dL",
        "critical_low": 7.0,
        "critical_high": 20.0,
        "source": "CLSI / Kost GJ Critical Limits Consensus",
        "source_version": "2026.1",
        "low_assoc": "Severe anemia or acute blood loss potential; requires urgent clinician correlation.",
        "high_assoc": "Extreme polycythemia or severe hemoconcentration; requires clinician review.",
    },
    {
        "canonical_name": "Platelets",
        "unit": "10^3/uL",
        "critical_low": 20.0,
        "critical_high": 1000.0,
        "source": "CLSI / CAP Critical Limits Standards",
        "source_version": "2026.1",
        "low_assoc": "Severe thrombocytopenia with elevated spontaneous bleeding risk; requires urgent clinician review.",
        "high_assoc": "Extreme thrombocytosis; requires clinician evaluation.",
    },
    {
        "canonical_name": "WBC",
        "unit": "10^3/uL",
        "critical_low": 1.5,
        "critical_high": 30.0,
        "source": "CLSI / CAP Critical Limits Standards",
        "source_version": "2026.1",
        "low_assoc": "Severe leukopenia / agranulocytosis; heightened infection vulnerability.",
        "high_assoc": "Marked leukocytosis or leukemoid reaction; requires prompt clinician evaluation.",
    },
    {
        "canonical_name": "Fasting Blood Glucose",
        "unit": "mg/dL",
        "critical_low": 50.0,
        "critical_high": 400.0,
        "source": "ADA Critical Value Guidelines / Kost Consensus",
        "source_version": "2026.1",
        "low_assoc": "Critical hypoglycemia; potential for neuroglycopenic symptoms and acute metabolic compromise.",
        "high_assoc": "Severe hyperglycemia; potential for acute hyperosmolar or ketoacidotic metabolic dysregulation.",
    },
    {
        "canonical_name": "Serum Creatinine",
        "unit": "mg/dL",
        "critical_low": None,
        "critical_high": 5.0,
        "source": "KDIGO Acute Kidney Injury Consensus",
        "source_version": "2026.1",
        "high_assoc": "Marked acute or chronic renal excretory failure; requires urgent clinical review.",
    },
    {
        "canonical_name": "Total Bilirubin",
        "unit": "mg/dL",
        "critical_low": None,
        "critical_high": 15.0,
        "source": "AASLD Clinical Guidance",
        "source_version": "2026.1",
        "high_assoc": "Severe hyperbilirubinemia; indicates profound hepatic dysfunction or high-grade biliary obstruction.",
    },
]


class CriticalValueRule(BaseClinicalRule):
    """Explicitly configured, source-backed critical threshold rule."""

    def __init__(self):
        super().__init__(
            rule_id="CRITICAL_VALUE_001",
            rule_name="Standard Critical Laboratory Alert Rule",
            rule_version="1.0.0",
            rule_type="CRITICAL",
            applicable_analytes=[item["canonical_name"] for item in CRITICAL_THRESHOLDS_CONFIG],
            severity=FindingSeverityEnum.CRITICAL.value,
            source="CLSI / CAP / Kost GJ Critical Limits Consensus Standards",
            source_version="2026.1",
            enabled=True,
        )

    def evaluate(self, context: Dict[str, Any]) -> List[RuleEvaluationResult]:
        results: List[RuleEvaluationResult] = []
        entity_evaluations = context.get("entity_evaluations", [])

        # Build lookup for critical thresholds
        crit_map = {item["canonical_name"].lower(): item for item in CRITICAL_THRESHOLDS_CONFIG}

        for item in entity_evaluations:
            entity = item.get("entity")
            if not entity or entity.review_status == "REJECTED":
                continue

            cname = (entity.canonical_name or getattr(entity, "raw_name", "")).strip().lower()
            if cname not in crit_map:
                continue

            cfg = crit_map[cname]
            val = entity.numeric_value
            unit = entity.normalized_unit or entity.original_unit or ""

            # Check unit compatibility
            if unit.lower() != cfg["unit"].lower():
                continue

            if val is None:
                continue

            analyte_title = getattr(entity, "raw_name", None) or entity.canonical_name or "Unknown Analyte"
            evidence = [{
                "entity_id": entity.id,
                "analyte": analyte_title,
                "value": entity.value_text or str(val),
                "numeric_value": val,
                "unit": unit,
                "page_number": entity.page_number,
                "source_text": entity.source_text,
                "confidence": entity.confidence,
                "review_status": entity.review_status,
            }]

            # Check critical low
            if cfg.get("critical_low") is not None and val < cfg["critical_low"]:
                results.append(
                    RuleEvaluationResult(
                        is_triggered=True,
                        finding_type=FindingTypeEnum.CRITICAL_LAB.value,
                        analyte=analyte_title,
                        value=str(val),
                        normalized_value=val,
                        unit=unit,
                        status=FindingStatusEnum.CRITICAL_LOW.value,
                        severity=FindingSeverityEnum.CRITICAL.value,
                        title=f"Critical Low: {analyte_title} ({val} {unit})",
                        explanation=f"The reported {analyte_title} value is below the established critical threshold of {cfg['critical_low']} {unit}.",
                        clinical_association=cfg.get("low_assoc"),
                        evidence=evidence,
                        confidence=round(1.0 if entity.review_status == "ACCEPTED" else entity.confidence, 2),
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        reference_source=cfg["source"],
                        reference_source_version=cfg["source_version"],
                        requires_review=(entity.review_status != "ACCEPTED"),
                    )
                )

            # Check critical high
            elif cfg.get("critical_high") is not None and val > cfg["critical_high"]:
                results.append(
                    RuleEvaluationResult(
                        is_triggered=True,
                        finding_type=FindingTypeEnum.CRITICAL_LAB.value,
                        analyte=analyte_title,
                        value=str(val),
                        normalized_value=val,
                        unit=unit,
                        status=FindingStatusEnum.CRITICAL_HIGH.value,
                        severity=FindingSeverityEnum.CRITICAL.value,
                        title=f"Critical High: {analyte_title} ({val} {unit})",
                        explanation=f"The reported {analyte_title} value is above the established critical threshold of {cfg['critical_high']} {unit}.",
                        clinical_association=cfg.get("high_assoc"),
                        evidence=evidence,
                        confidence=round(1.0 if entity.review_status == "ACCEPTED" else entity.confidence, 2),
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        reference_source=cfg["source"],
                        reference_source_version=cfg["source_version"],
                        requires_review=(entity.review_status != "ACCEPTED"),
                    )
                )

        return results
