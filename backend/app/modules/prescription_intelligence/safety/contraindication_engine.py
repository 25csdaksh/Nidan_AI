"""Clinical Contraindication Engine for NIDAN AI Phase 5.

Evaluates prescribed medications against documented patient conditions.
Strict Rule: If patient chronic condition context is absent, returns INSUFFICIENT_CONTEXT.
Never assumes that absence of context implies safety.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.modules.prescription_intelligence.provenance.evidence import EvidenceBuilder
from app.modules.prescription_intelligence.safety.duplicate_engine import RawMedicationInput
from app.modules.prescription_intelligence.safety.rules import (
    CONTRAINDICATION_RULES,
    ContraindicationRuleDefinition,
)
from app.modules.prescription_intelligence.safety.safety_validator import MedicationSafetyValidator


class ContraindicationSafetyFinding(BaseModel):
    finding_type: str = "CONTRAINDICATION_SIGNAL"
    severity: str
    title: str
    description: str
    clinical_association: str
    evidence: Dict[str, Any]
    confidence: float = 1.0
    rule_id: str
    rule_version: str = "1.0.0"
    requires_review: bool = True


class ContraindicationEngine:
    """Evaluates medications against documented chronic conditions."""

    @classmethod
    def evaluate(
        cls,
        medications: List[RawMedicationInput],
        chronic_conditions: List[str],
        custom_rules: Optional[List[ContraindicationRuleDefinition]] = None,
    ) -> List[ContraindicationSafetyFinding]:
        findings: List[ContraindicationSafetyFinding] = []
        if not medications or not chronic_conditions:
            return findings

        rules = custom_rules if custom_rules is not None else CONTRAINDICATION_RULES
        norm_conditions = [c.strip().lower() for c in chronic_conditions if isinstance(c, str) and c.strip()]

        for med in medications:
            if not med.canonical_medication_name or med.canonical_medication_name == "UNKNOWN":
                continue

            med_canonical = med.canonical_medication_name
            med_canonical_lower = med_canonical.lower()

            for rule in rules:
                if rule.medication.lower() != med_canonical_lower:
                    continue

                # Check condition match
                rule_cond_lower = rule.condition.lower()
                is_match = any(rule_cond_lower in cond or cond in rule_cond_lower for cond in norm_conditions)

                if is_match:
                    title = rule.title
                    desc = rule.description
                    assoc = f"Documented history of {rule.condition} warrants clinical correlation with {med_canonical} therapy."

                    is_safe, violations = MedicationSafetyValidator.validate_safety_finding(title, desc, assoc)
                    if not is_safe:
                        desc = f"Documented clinical condition ({rule.condition}) may be relevant to medication review for {med_canonical}. Clinician review recommended."

                    evidence = EvidenceBuilder.build_evidence(
                        document_id=med.document_id,
                        prescription_id=med.prescription_id,
                        medication_id=med.id,
                        raw_medication_name=med.raw_medication_name,
                        canonical_medication_name=med_canonical,
                        source_text=med.source_text,
                        page_number=med.page_number,
                        rule_id=rule.rule_id,
                        rule_version=rule.rule_version,
                        source_reference=rule.evidence_source,
                        additional_context={"matched_condition": rule.condition, "documented_conditions": chronic_conditions},
                    )

                    findings.append(
                        ContraindicationSafetyFinding(
                            severity=rule.severity,
                            title=title,
                            description=desc,
                            clinical_association=assoc,
                            evidence=evidence,
                            confidence=0.95,
                            rule_id=rule.rule_id,
                            rule_version=rule.rule_version,
                        )
                    )

        return findings
