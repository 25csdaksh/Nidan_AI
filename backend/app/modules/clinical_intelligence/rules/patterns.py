from typing import Any, Dict, List, Optional
from app.modules.clinical_intelligence.rules.base import BaseClinicalRule, RuleEvaluationResult
from app.modules.clinical_intelligence.models import (
    FindingTypeEnum,
    FindingStatusEnum,
    FindingSeverityEnum,
)


class MultiMarkerPatternRule(BaseClinicalRule):
    """Deterministic Multi-Marker Pattern Detection Rule with traceable multi-entity evidence."""

    def __init__(self):
        super().__init__(
            rule_id="PATTERN_ENGINE_001",
            rule_name="Standard Multi-Marker Clinical Pattern Engine",
            rule_version="1.0.0",
            rule_type="PATTERN",
            applicable_analytes=[
                "Hemoglobin", "MCV", "MCH", "Ferritin", "Serum Iron", "TIBC",
                "Vitamin B12", "Folic Acid",
                "Fasting Blood Glucose", "HbA1c",
                "Serum Creatinine", "eGFR", "BUN",
                "ALT", "AST", "Total Bilirubin", "Alkaline Phosphatase",
            ],
            severity=FindingSeverityEnum.MODERATE.value,
            source="Evidence-Based Laboratory Medicine Pattern Criteria",
            source_version="2026.1",
            enabled=True,
        )

    def evaluate(self, context: Dict[str, Any]) -> List[RuleEvaluationResult]:
        results: List[RuleEvaluationResult] = []
        entity_evaluations = context.get("entity_evaluations", [])

        # Build analyte map indexed by lowercase canonical name
        analyte_map: Dict[str, Dict[str, Any]] = {}
        for item in entity_evaluations:
            ent = item.get("entity")
            rr = item.get("resolved_range")
            if not ent or ent.review_status == "REJECTED":
                continue

            cname = (ent.canonical_name or getattr(ent, "raw_name", "")).strip().lower()
            val = ent.numeric_value
            if val is None:
                continue

            # Check status relative to resolved range or standard threshold
            is_low = False
            is_high = False
            if rr and rr.is_resolved:
                if rr.lower_bound is not None and val < rr.lower_bound:
                    is_low = True
                if rr.upper_bound is not None and val > rr.upper_bound:
                    is_high = True

            analyte_map[cname] = {
                "entity": ent,
                "value": val,
                "unit": ent.normalized_unit or ent.original_unit,
                "is_low": is_low,
                "is_high": is_high,
                "confidence": ent.confidence,
                "review_status": ent.review_status,
                "resolved_range": rr,
            }

        # Helper to construct evidence list from matching entities
        def build_evidence(matched_names: List[str]) -> List[Dict[str, Any]]:
            ev_list = []
            for n in matched_names:
                info = analyte_map[n]
                ent = info["entity"]
                ev_list.append({
                    "entity_id": ent.id,
                    "analyte": getattr(ent, "raw_name", None) or ent.canonical_name or "Unknown Analyte",
                    "value": ent.value_text or str(info["value"]),
                    "numeric_value": info["value"],
                    "unit": info["unit"],
                    "status": "LOW" if info["is_low"] else ("HIGH" if info["is_high"] else "NORMAL"),
                    "page_number": ent.page_number,
                    "source_text": ent.source_text,
                    "confidence": ent.confidence,
                    "review_status": ent.review_status,
                })
            return ev_list

        def calc_confidence(matched_names: List[str]) -> float:
            confs = [analyte_map[n]["confidence"] for n in matched_names]
            if not confs:
                return 0.8
            # If all are accepted, boost to 1.0; else average
            if all(analyte_map[n]["review_status"] == "ACCEPTED" for n in matched_names):
                return 1.0
            return round(sum(confs) / len(confs), 2)

        # -------------------------------------------------------------
        # Pattern A: Possible Iron-Deficiency Pattern
        # Supporting: low Hemoglobin, low MCV, low MCH, low Ferritin, low Serum Iron, elevated TIBC
        # Requires >= 2 supporting markers
        # -------------------------------------------------------------
        iron_matches = []
        if analyte_map.get("hemoglobin", {}).get("is_low"):
            iron_matches.append("hemoglobin")
        if analyte_map.get("mcv", {}).get("is_low") or (analyte_map.get("mcv", {}).get("value", 100) < 80.0):
            iron_matches.append("mcv")
        if analyte_map.get("mch", {}).get("is_low") or (analyte_map.get("mch", {}).get("value", 100) < 27.0):
            iron_matches.append("mch")
        if analyte_map.get("ferritin", {}).get("is_low") or (analyte_map.get("ferritin", {}).get("value", 100) < 30.0):
            iron_matches.append("ferritin")
        if analyte_map.get("serum iron", {}).get("is_low") or (analyte_map.get("serum iron", {}).get("value", 100) < 60.0):
            iron_matches.append("serum iron")
        if analyte_map.get("tibc", {}).get("is_high"):
            iron_matches.append("tibc")

        # Deduplicate
        iron_matches = list(dict.fromkeys(iron_matches))
        if len(iron_matches) >= 2:
            results.append(
                RuleEvaluationResult(
                    is_triggered=True,
                    finding_type=FindingTypeEnum.PATTERN.value,
                    analyte="Iron Metabolism & Erythrocyte Panel",
                    value=f"{len(iron_matches)} Concordant Markers",
                    unit="markers",
                    status=FindingStatusEnum.LOW.value,
                    severity=FindingSeverityEnum.MODERATE.value,
                    title="Possible Iron-Deficiency Laboratory Pattern",
                    explanation=f"A pattern of {len(iron_matches)} concordant markers ({', '.join(iron_matches).title()}) was identified.",
                    clinical_association="Pattern may be consistent with iron deficiency; clinical correlation recommended.",
                    evidence=build_evidence(iron_matches),
                    confidence=calc_confidence(iron_matches),
                    rule_id="IRON_PATTERN_001",
                    rule_version="1.0.0",
                    reference_source="CLSI / WHO Laboratory Guidelines",
                    reference_source_version="2026.1",
                    requires_review=any(analyte_map[n]["review_status"] != "ACCEPTED" for n in iron_matches),
                )
            )

        # -------------------------------------------------------------
        # Pattern B: Possible Macrocytic Pattern
        # Supporting: high MCV (>96 or is_high), low Vitamin B12, low Folic Acid
        # Requires >= 2 supporting markers
        # -------------------------------------------------------------
        macro_matches = []
        if analyte_map.get("mcv", {}).get("is_high") or (analyte_map.get("mcv", {}).get("value", 0) > 96.0):
            macro_matches.append("mcv")
        if analyte_map.get("vitamin b12", {}).get("is_low") or (analyte_map.get("vitamin b12", {}).get("value", 1000) < 200.0):
            macro_matches.append("vitamin b12")
        if analyte_map.get("folic acid", {}).get("is_low") or (analyte_map.get("folic acid", {}).get("value", 100) < 3.0):
            macro_matches.append("folic acid")

        macro_matches = list(dict.fromkeys(macro_matches))
        if len(macro_matches) >= 2:
            results.append(
                RuleEvaluationResult(
                    is_triggered=True,
                    finding_type=FindingTypeEnum.PATTERN.value,
                    analyte="Erythrocyte Indices & Cobalamin/Folate Panel",
                    value=f"{len(macro_matches)} Concordant Markers",
                    unit="markers",
                    status=FindingStatusEnum.HIGH.value,
                    severity=FindingSeverityEnum.MODERATE.value,
                    title="Possible Macrocytic Laboratory Pattern",
                    explanation=f"Macrocytic erythrocyte indices and cofactor marker changes observed ({', '.join(macro_matches).title()}).",
                    clinical_association="Macrocytic pattern observed in the available laboratory data; clinical correlation recommended.",
                    evidence=build_evidence(macro_matches),
                    confidence=calc_confidence(macro_matches),
                    rule_id="MACROCYTIC_PATTERN_001",
                    rule_version="1.0.0",
                    reference_source="ICSH / AACC Laboratory Guidelines",
                    reference_source_version="2026.1",
                    requires_review=any(analyte_map[n]["review_status"] != "ACCEPTED" for n in macro_matches),
                )
            )

        # -------------------------------------------------------------
        # Pattern C: Possible Glycemic Abnormality Pattern
        # Supporting: elevated Fasting Blood Glucose, elevated HbA1c
        # Requires both or either with high severity
        # -------------------------------------------------------------
        glycemic_matches = []
        if analyte_map.get("fasting blood glucose", {}).get("is_high") or (analyte_map.get("fasting blood glucose", {}).get("value", 0) >= 126.0):
            glycemic_matches.append("fasting blood glucose")
        if analyte_map.get("hba1c", {}).get("is_high") or (analyte_map.get("hba1c", {}).get("value", 0) >= 6.5):
            glycemic_matches.append("hba1c")

        glycemic_matches = list(dict.fromkeys(glycemic_matches))
        if len(glycemic_matches) >= 2:
            results.append(
                RuleEvaluationResult(
                    is_triggered=True,
                    finding_type=FindingTypeEnum.PATTERN.value,
                    analyte="Glycemic Control Panel",
                    value=f"{len(glycemic_matches)} Concordant Markers",
                    unit="markers",
                    status=FindingStatusEnum.HIGH.value,
                    severity=FindingSeverityEnum.HIGH.value,
                    title="Possible Glycemic Abnormality Pattern",
                    explanation="Elevated fasting blood glucose and HbA1c levels observed concordantly.",
                    clinical_association="Elevated glycemic markers observed; clinical correlation recommended.",
                    evidence=build_evidence(glycemic_matches),
                    confidence=calc_confidence(glycemic_matches),
                    rule_id="GLYCEMIC_PATTERN_001",
                    rule_version="1.0.0",
                    reference_source="ADA Standards of Care",
                    reference_source_version="2026.1",
                    requires_review=any(analyte_map[n]["review_status"] != "ACCEPTED" for n in glycemic_matches),
                )
            )

        # -------------------------------------------------------------
        # Pattern D: Possible Renal-Function Abnormality Pattern
        # Supporting: elevated Serum Creatinine, reduced eGFR, elevated BUN
        # Requires >= 2 supporting markers
        # -------------------------------------------------------------
        renal_matches = []
        if analyte_map.get("serum creatinine", {}).get("is_high") or (analyte_map.get("serum creatinine", {}).get("value", 0) > 1.3):
            renal_matches.append("serum creatinine")
        if analyte_map.get("egfr", {}).get("is_low") or (analyte_map.get("egfr", {}).get("value", 100) < 60.0):
            renal_matches.append("egfr")
        if analyte_map.get("bun", {}).get("is_high") or (analyte_map.get("bun", {}).get("value", 0) > 20.0):
            renal_matches.append("bun")

        renal_matches = list(dict.fromkeys(renal_matches))
        if len(renal_matches) >= 2:
            results.append(
                RuleEvaluationResult(
                    is_triggered=True,
                    finding_type=FindingTypeEnum.PATTERN.value,
                    analyte="Renal Function Panel",
                    value=f"{len(renal_matches)} Concordant Markers",
                    unit="markers",
                    status=FindingStatusEnum.HIGH.value,
                    severity=FindingSeverityEnum.HIGH.value,
                    title="Possible Renal-Function Abnormality Pattern",
                    explanation=f"Concordant renal filtration and clearance abnormalities observed ({', '.join(renal_matches).title()}).",
                    clinical_association="Renal-function-related laboratory abnormalities are present; clinical correlation recommended.",
                    evidence=build_evidence(renal_matches),
                    confidence=calc_confidence(renal_matches),
                    rule_id="RENAL_PATTERN_001",
                    rule_version="1.0.0",
                    reference_source="KDIGO Clinical Practice Guidelines",
                    reference_source_version="2026.1",
                    requires_review=any(analyte_map[n]["review_status"] != "ACCEPTED" for n in renal_matches),
                )
            )

        # -------------------------------------------------------------
        # Pattern E: Possible Hepatic Pattern
        # Supporting: elevated ALT, elevated AST, elevated Total Bilirubin, elevated Alkaline Phosphatase
        # Requires >= 2 supporting markers
        # -------------------------------------------------------------
        hepatic_matches = []
        if analyte_map.get("alt", {}).get("is_high"):
            hepatic_matches.append("alt")
        if analyte_map.get("ast", {}).get("is_high"):
            hepatic_matches.append("ast")
        if analyte_map.get("total bilirubin", {}).get("is_high"):
            hepatic_matches.append("total bilirubin")
        if analyte_map.get("alkaline phosphatase", {}).get("is_high"):
            hepatic_matches.append("alkaline phosphatase")

        hepatic_matches = list(dict.fromkeys(hepatic_matches))
        if len(hepatic_matches) >= 2:
            results.append(
                RuleEvaluationResult(
                    is_triggered=True,
                    finding_type=FindingTypeEnum.PATTERN.value,
                    analyte="Hepatic Enzyme & Biomarker Panel",
                    value=f"{len(hepatic_matches)} Concordant Markers",
                    unit="markers",
                    status=FindingStatusEnum.HIGH.value,
                    severity=FindingSeverityEnum.MODERATE.value,
                    title="Possible Hepatic Laboratory Pattern",
                    explanation=f"Elevated hepatic enzymes / biliary excretion markers observed ({', '.join(hepatic_matches).upper()}).",
                    clinical_association="Hepatic enzyme and marker abnormalities observed; clinical correlation recommended.",
                    evidence=build_evidence(hepatic_matches),
                    confidence=calc_confidence(hepatic_matches),
                    rule_id="HEPATIC_PATTERN_001",
                    rule_version="1.0.0",
                    reference_source="AASLD Practice Guidelines",
                    reference_source_version="2026.1",
                    requires_review=any(analyte_map[n]["review_status"] != "ACCEPTED" for n in hepatic_matches),
                )
            )

        return results
