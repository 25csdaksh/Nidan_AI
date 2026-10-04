"""Drug-Drug Interaction (DDI) Engine for NIDAN AI Phase 5.

Evaluates co-prescribed and active medications against curated, versioned interaction rules.
Strict Rule: An LLM is NEVER the authoritative drug interaction database.
Only validated, rule-backed pairs are matched.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.modules.prescription_intelligence.provenance.evidence import EvidenceBuilder
from app.modules.prescription_intelligence.safety.duplicate_engine import RawMedicationInput
from app.modules.prescription_intelligence.safety.rules import (
    DRUG_INTERACTION_RULES,
    InteractionRuleDefinition,
)
from app.modules.prescription_intelligence.safety.safety_validator import MedicationSafetyValidator


class InteractionSafetyFinding(BaseModel):
    finding_type: str = "DRUG_DRUG_INTERACTION"
    severity: str
    title: str
    description: str
    clinical_association: str
    evidence: Dict[str, Any]
    confidence: float = 1.0
    rule_id: str
    rule_version: str = "1.0.0"
    requires_review: bool = True


class InteractionEngine:
    """Evaluates pairs of medications against curated drug-drug interaction rules."""

    @classmethod
    def evaluate(
        cls,
        medications: List[RawMedicationInput],
        custom_rules: Optional[List[InteractionRuleDefinition]] = None,
    ) -> List[InteractionSafetyFinding]:
        findings: List[InteractionSafetyFinding] = []
        if len(medications) < 2:
            return findings

        rules = custom_rules if custom_rules is not None else DRUG_INTERACTION_RULES

        # Map canonical drug names to medication inputs
        drug_map: Dict[str, List[RawMedicationInput]] = {}
        for m in medications:
            if m.canonical_medication_name and m.canonical_medication_name != "UNKNOWN":
                drug_map.setdefault(m.canonical_medication_name.lower(), []).append(m)

        evaluated_pairs = set()

        for rule in rules:
            if not rule.active:
                continue

            drug_a_low = rule.drug_a.lower()
            drug_b_low = rule.drug_b.lower()

            # Order-independent pair key
            pair_key = tuple(sorted([drug_a_low, drug_b_low]))
            if pair_key in evaluated_pairs:
                continue

            if drug_a_low in drug_map and drug_b_low in drug_map:
                evaluated_pairs.add(pair_key)
                med_a = drug_map[drug_a_low][0]
                med_b = drug_map[drug_b_low][0]

                # Validate safety guardrails
                is_safe, violations = MedicationSafetyValidator.validate_safety_finding(
                    rule.title, rule.description, rule.clinical_association
                )

                desc = rule.description
                if not is_safe:
                    desc = f"Potential medication interaction identified between {rule.drug_a} and {rule.drug_b}. Clinician review recommended."

                evidence = EvidenceBuilder.build_evidence(
                    document_id=med_a.document_id,
                    prescription_id=med_a.prescription_id,
                    medication_id=med_a.id,
                    raw_medication_name=f"{med_a.raw_medication_name} + {med_b.raw_medication_name}",
                    canonical_medication_name=f"{rule.drug_a} + {rule.drug_b}",
                    source_text=f"A: {med_a.source_text} | B: {med_b.source_text}",
                    page_number=med_a.page_number,
                    rule_id=rule.rule_id,
                    rule_version=rule.rule_version,
                    source_reference=rule.evidence_source,
                    additional_context={
                        "interaction_type": rule.interaction_type,
                        "drug_a": rule.drug_a,
                        "drug_b": rule.drug_b,
                        "med_a_id": med_a.id,
                        "med_b_id": med_b.id,
                    },
                )

                findings.append(
                    InteractionSafetyFinding(
                        severity=rule.severity,
                        title=rule.title,
                        description=desc,
                        clinical_association=rule.clinical_association,
                        evidence=evidence,
                        confidence=0.98,
                        rule_id=rule.rule_id,
                        rule_version=rule.rule_version,
                        requires_review=rule.requires_review,
                    )
                )

        return findings
