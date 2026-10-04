from typing import Any, Dict, List, Optional
from app.modules.clinical_intelligence.rules.base import BaseClinicalRule, RuleEvaluationResult
from app.modules.clinical_intelligence.models import (
    FindingTypeEnum,
    FindingStatusEnum,
    FindingSeverityEnum,
)

DEFICIENCY_CONFIGS = [
    {
        "canonical_name": "Ferritin",
        "threshold": 30.0,
        "operator": "<",
        "unit": "ng/mL",
        "title": "Serum Ferritin below configured threshold",
        "explanation": "Reported serum ferritin is below 30.0 ng/mL, which may indicate depleted iron reserves.",
        "clinical_association": "Low ferritin levels may be associated with iron deficiency or depleted body iron stores; clinical correlation recommended.",
        "source": "WHO Guidelines on Iron Deficiency & Ferritin Thresholds",
        "source_version": "2026.1",
        "severity": FindingSeverityEnum.MODERATE.value,
    },
    {
        "canonical_name": "Serum Iron",
        "threshold": 60.0,
        "operator": "<",
        "unit": "ug/dL",
        "title": "Serum Iron below configured threshold",
        "explanation": "Reported serum iron is below 60.0 ug/dL, which may reflect diminished circulating iron.",
        "clinical_association": "Low serum iron levels may be associated with insufficient dietary intake, malabsorption, or ongoing blood loss; clinical correlation recommended.",
        "source": "Tietz Clinical Laboratory Reference",
        "source_version": "2026.1",
        "severity": FindingSeverityEnum.MODERATE.value,
    },
    {
        "canonical_name": "Vitamin B12",
        "threshold": 200.0,
        "operator": "<",
        "unit": "pg/mL",
        "title": "Vitamin B12 below configured threshold",
        "explanation": "Reported vitamin B12 is below 200.0 pg/mL, which indicates suboptimal cobalamin levels.",
        "clinical_association": "Low vitamin B12 levels may be associated with cobalamin deficiency, dietary deficits, or absorption disorders; clinical correlation recommended.",
        "source": "AACC / Endocrine Society Clinical Guidelines",
        "source_version": "2026.1",
        "severity": FindingSeverityEnum.MODERATE.value,
    },
    {
        "canonical_name": "Vitamin D, 25-OH",
        "threshold": 20.0,
        "operator": "<",
        "unit": "ng/mL",
        "title": "Vitamin D below configured threshold",
        "explanation": "Reported 25-hydroxyvitamin D is below 20.0 ng/mL, indicating insufficient serum concentrations.",
        "clinical_association": "Low 25-hydroxyvitamin D levels may be associated with vitamin D deficiency, reduced cutaneous synthesis, or malabsorption; clinical correlation recommended.",
        "source": "Endocrine Society Clinical Practice Guidelines",
        "source_version": "2026.1",
        "severity": FindingSeverityEnum.MODERATE.value,
    },
    {
        "canonical_name": "MCV",
        "threshold": 80.0,
        "operator": "<",
        "unit": "fL",
        "title": "Mean Corpuscular Volume (MCV) below configured threshold",
        "explanation": "Reported MCV is below 80.0 fL, indicating microcytic erythrocyte morphology.",
        "clinical_association": "Microcytosis (low MCV) may be associated with iron deficiency, hemoglobinopathies (e.g. thalassemia trait), or anemia of chronic disease; clinical correlation recommended.",
        "source": "ICSH Guidelines for Blood Cell Morphology",
        "source_version": "2026.1",
        "severity": FindingSeverityEnum.LOW.value,
    },
    {
        "canonical_name": "MCH",
        "threshold": 27.0,
        "operator": "<",
        "unit": "pg",
        "title": "Mean Corpuscular Hemoglobin (MCH) below configured threshold",
        "explanation": "Reported MCH is below 27.0 pg, indicating hypochromic erythrocyte morphology.",
        "clinical_association": "Hypochromia (low MCH) may be associated with impaired heme synthesis or iron deficiency; clinical correlation recommended.",
        "source": "ICSH Guidelines for Blood Cell Morphology",
        "source_version": "2026.1",
        "severity": FindingSeverityEnum.LOW.value,
    },
]


class DeficiencyDetectionRule(BaseClinicalRule):
    """Controlled, single-analyte deficiency detection rule with non-diagnostic language."""

    def __init__(self):
        super().__init__(
            rule_id="DEFICIENCY_RULE_001",
            rule_name="Controlled Laboratory Deficiency Marker Rule",
            rule_version="1.0.0",
            rule_type="POSSIBLE_DEFICIENCY",
            applicable_analytes=[c["canonical_name"] for c in DEFICIENCY_CONFIGS],
            severity=FindingSeverityEnum.MODERATE.value,
            source="WHO / Endocrine Society / AACC Laboratory Guidelines",
            source_version="2026.1",
            enabled=True,
        )

    def evaluate(self, context: Dict[str, Any]) -> List[RuleEvaluationResult]:
        results: List[RuleEvaluationResult] = []
        entity_evaluations = context.get("entity_evaluations", [])

        cfg_map = {item["canonical_name"].lower(): item for item in DEFICIENCY_CONFIGS}

        for item in entity_evaluations:
            entity = item.get("entity")
            if not entity or entity.review_status == "REJECTED":
                continue

            cname = (entity.canonical_name or getattr(entity, "raw_name", "")).strip().lower()
            if cname not in cfg_map:
                continue

            cfg = cfg_map[cname]
            val = entity.numeric_value
            unit = entity.normalized_unit or entity.original_unit or ""

            if val is None or unit.lower() != cfg["unit"].lower():
                continue

            # Check threshold
            triggered = False
            if cfg["operator"] == "<" and val < cfg["threshold"]:
                triggered = True
            elif cfg["operator"] == ">" and val > cfg["threshold"]:
                triggered = True

            if triggered:
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

                results.append(
                    RuleEvaluationResult(
                        is_triggered=True,
                        finding_type=FindingTypeEnum.POSSIBLE_DEFICIENCY.value,
                        analyte=analyte_title,
                        value=str(val),
                        normalized_value=val,
                        unit=unit,
                        status=FindingStatusEnum.LOW.value,
                        severity=cfg["severity"],
                        title=cfg["title"],
                        explanation=cfg["explanation"],
                        clinical_association=cfg["clinical_association"],
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
