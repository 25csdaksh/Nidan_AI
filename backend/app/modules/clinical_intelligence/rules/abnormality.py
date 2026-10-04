from typing import Any, Dict, List, Optional
from app.modules.clinical_intelligence.rules.base import BaseClinicalRule, RuleEvaluationResult
from app.modules.clinical_intelligence.models import (
    FindingTypeEnum,
    FindingStatusEnum,
    FindingSeverityEnum,
)

# Standardized non-diagnostic controlled clinical associations
CONTROLLED_ASSOCIATIONS = {
    "Hemoglobin": {
        "LOW": "Low hemoglobin levels may be associated with blood loss, decreased red cell production, or anemias of various etiologies; clinical correlation is required.",
        "HIGH": "Elevated hemoglobin levels may be associated with dehydration, polycythemia, or chronic hypoxia; clinical correlation is recommended.",
    },
    "WBC": {
        "LOW": "Low white blood cell count (leukopenia) may be associated with viral infections, bone marrow suppression, or immune conditions; clinical review recommended.",
        "HIGH": "Elevated white blood cell count (leukocytosis) may be associated with physiological stress, inflammation, or infection; clinical correlation recommended.",
    },
    "Platelets": {
        "LOW": "Low platelet count (thrombocytopenia) may be associated with increased destruction, sequestration, or decreased production; clinical review recommended.",
        "HIGH": "Elevated platelet count (thrombocytosis) may be associated with reactive inflammatory states, iron deficiency, or myeloproliferative processes; clinical correlation recommended.",
    },
    "Fasting Blood Glucose": {
        "LOW": "Low fasting glucose may be associated with hypoglycemia, medication effects, or metabolic dysregulation; clinical evaluation recommended.",
        "HIGH": "Elevated fasting blood glucose may be associated with impaired glucose tolerance, insulin resistance, or diabetes mellitus; clinical correlation recommended.",
    },
    "HbA1c": {
        "HIGH": "Elevated glycated hemoglobin (HbA1c) reflects average glycemia over the preceding 2-3 months and may indicate prediabetes or diabetes; clinical correlation recommended.",
    },
    "Serum Creatinine": {
        "HIGH": "Elevated serum creatinine may indicate reduced glomerular filtration rate or impaired renal excretory function; clinical correlation recommended.",
    },
    "eGFR": {
        "LOW": "Reduced estimated glomerular filtration rate (eGFR) may be consistent with decreased kidney function; clinical correlation recommended.",
    },
    "BUN": {
        "HIGH": "Elevated blood urea nitrogen (BUN) may be associated with renal impairment, dehydration, or increased protein catabolism; clinical correlation recommended.",
    },
    "ALT": {
        "HIGH": "Elevated alanine aminotransferase (ALT) is an intracellular enzyme marker that may reflect hepatocellular injury or inflammation; clinical correlation recommended.",
    },
    "AST": {
        "HIGH": "Elevated aspartate aminotransferase (AST) may reflect hepatic, cardiac, or skeletal muscle cellular turnover; clinical correlation recommended.",
    },
    "Total Bilirubin": {
        "HIGH": "Elevated total bilirubin may be associated with biliary obstruction, impaired hepatic clearance, or hemolysis; clinical correlation recommended.",
    },
    "Alkaline Phosphatase": {
        "HIGH": "Elevated alkaline phosphatase (ALP) may reflect hepatobiliary obstruction or increased osteoblastic bone turnover; clinical correlation recommended.",
    },
    "Total Cholesterol": {
        "HIGH": "Elevated total cholesterol may contribute to atherogenic risk profiles; clinical correlation and lifestyle evaluation recommended.",
    },
    "LDL Cholesterol": {
        "HIGH": "Elevated LDL cholesterol is associated with cardiovascular risk; clinical correlation recommended.",
    },
    "Triglycerides": {
        "HIGH": "Elevated triglycerides may be associated with metabolic syndrome, familial dyslipidemia, or dietary factors; clinical correlation recommended.",
    },
    "TSH": {
        "LOW": "Suppressed thyroid-stimulating hormone (TSH) may be consistent with excessive thyroid hormone action or hyperthyroidism; clinical correlation recommended.",
        "HIGH": "Elevated thyroid-stimulating hormone (TSH) may indicate diminished thyroid hormone output or primary hypothyroidism; clinical correlation recommended.",
    },
    "Ferritin": {
        "LOW": "Low serum ferritin is a specific indicator of depleted body iron stores; clinical correlation recommended.",
        "HIGH": "Elevated ferritin may reflect iron overload, acute phase inflammation, or liver pathology; clinical correlation recommended.",
    },
    "Serum Iron": {
        "LOW": "Low serum iron may reflect diminished circulating iron availability; clinical correlation recommended.",
    },
    "Vitamin B12": {
        "LOW": "Low serum vitamin B12 levels may be associated with dietary insufficiency, malabsorption, or pernicious anemia; clinical correlation recommended.",
    },
    "Vitamin D, 25-OH": {
        "LOW": "Low 25-hydroxyvitamin D levels may be associated with insufficient sun exposure, dietary deficit, or malabsorption; clinical correlation recommended.",
    },
}


class LabAbnormalityRule(BaseClinicalRule):
    """Deterministic, unit-validated abnormality evaluation against resolved reference ranges."""

    def __init__(self):
        super().__init__(
            rule_id="LAB_ABNORMALITY_001",
            rule_name="Standard Laboratory Abnormality Evaluation",
            rule_version="1.0.0",
            rule_type="ABNORMALITY",
            applicable_analytes=["*"],
            severity=FindingSeverityEnum.MODERATE.value,
            source="CLSI C28-A3 / Standard Clinical Laboratory Practice",
            source_version="2026.1",
            enabled=True,
        )

    def evaluate(self, context: Dict[str, Any]) -> List[RuleEvaluationResult]:
        results: List[RuleEvaluationResult] = []
        entity_evaluations = context.get("entity_evaluations", [])

        for item in entity_evaluations:
            entity = item.get("entity")
            resolved_range = item.get("resolved_range")
            if not entity:
                continue

            # Skip rejected entities
            if entity.review_status == "REJECTED":
                continue

            analyte_name = getattr(entity, "raw_name", None) or entity.canonical_name or "Unknown Analyte"
            val = entity.numeric_value
            unit = entity.normalized_unit or entity.original_unit or ""
            evidence = [{
                "entity_id": entity.id,
                "analyte": analyte_name,
                "value": entity.value_text or str(val),
                "numeric_value": val,
                "unit": unit,
                "page_number": entity.page_number,
                "source_text": entity.source_text,
                "confidence": entity.confidence,
                "review_status": entity.review_status,
            }]

            # Extraction quality & review requirement
            requires_review = (entity.confidence < 0.85 and entity.review_status != "ACCEPTED")

            # Check if reference range was unresolved
            if not resolved_range or not resolved_range.is_resolved:
                results.append(
                    RuleEvaluationResult(
                        is_triggered=True,
                        finding_type=FindingTypeEnum.DATA_QUALITY_WARNING.value,
                        analyte=analyte_name,
                        value=entity.value_text or str(val),
                        normalized_value=val,
                        unit=unit,
                        status=FindingStatusEnum.REFERENCE_RANGE_UNRESOLVED.value,
                        severity=FindingSeverityEnum.INFO.value,
                        title=f"{analyte_name} reference range unresolved",
                        explanation=resolved_range.resolution_reason if resolved_range else "Applicable reference range could not be resolved from available data.",
                        clinical_association=None,
                        evidence=evidence,
                        confidence=min(entity.confidence, 0.7),
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        reference_source="UNKNOWN",
                        reference_source_version=None,
                        requires_review=True,
                    )
                )
                continue

            # If numeric value is missing or unparseable
            if val is None:
                results.append(
                    RuleEvaluationResult(
                        is_triggered=True,
                        finding_type=FindingTypeEnum.DATA_QUALITY_WARNING.value,
                        analyte=analyte_name,
                        value=entity.value_text,
                        normalized_value=None,
                        unit=unit,
                        status=FindingStatusEnum.UNKNOWN.value,
                        severity=FindingSeverityEnum.INFO.value,
                        title=f"{analyte_name} numeric value unparseable",
                        explanation="The extracted laboratory result could not be parsed into a valid numerical quantity.",
                        clinical_association=None,
                        evidence=evidence,
                        confidence=0.5,
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        reference_source=resolved_range.source_type,
                        reference_source_version=resolved_range.source_version,
                        requires_review=True,
                    )
                )
                continue

            lower = resolved_range.lower_bound
            upper = resolved_range.upper_bound

            # Evaluation logic
            status = FindingStatusEnum.NORMAL.value
            severity = FindingSeverityEnum.INFO.value
            title = f"{analyte_name} within reference range"
            explanation = f"The reported {analyte_name} value ({val} {unit}) is within the applicable reference range."

            if lower is not None and val < lower:
                status = FindingStatusEnum.LOW.value
                severity = FindingSeverityEnum.MODERATE.value
                title = f"{analyte_name} below applicable reference range"
                explanation = f"The reported {analyte_name} value ({val} {unit}) is below the reference threshold of {lower} {unit}."
            elif upper is not None and val > upper:
                status = FindingStatusEnum.HIGH.value
                severity = FindingSeverityEnum.MODERATE.value
                title = f"{analyte_name} above applicable reference range"
                explanation = f"The reported {analyte_name} value ({val} {unit}) is above the reference threshold of {upper} {unit}."

            # Controlled clinical association lookup
            assoc_map = CONTROLLED_ASSOCIATIONS.get(analyte_name, {}) or CONTROLLED_ASSOCIATIONS.get(entity.canonical_name, {})
            clinical_assoc = assoc_map.get(status)

            # Confidence calculation: extraction confidence + bonus if reviewed
            finding_conf = entity.confidence
            if entity.review_status == "ACCEPTED":
                finding_conf = 1.0

            results.append(
                RuleEvaluationResult(
                    is_triggered=True,
                    finding_type=FindingTypeEnum.ABNORMAL_LAB.value if status != FindingStatusEnum.NORMAL.value else FindingTypeEnum.ABNORMAL_LAB.value,
                    analyte=analyte_name,
                    value=str(val),
                    normalized_value=val,
                    unit=unit,
                    status=status,
                    severity=severity,
                    title=title,
                    explanation=explanation,
                    clinical_association=clinical_assoc,
                    evidence=evidence,
                    confidence=round(finding_conf, 2),
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    reference_source=resolved_range.source_type,
                    reference_source_version=resolved_range.source_version,
                    requires_review=requires_review,
                )
            )

        return results
