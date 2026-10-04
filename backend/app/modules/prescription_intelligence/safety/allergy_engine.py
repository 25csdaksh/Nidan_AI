"""Medication Allergy Safety Engine for NIDAN AI Phase 5.

Cross-references prescribed medications with explicitly documented patient allergies.
Strict Rule: Evaluates only explicitly documented patient allergies. Never infers unrecorded allergies.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.modules.prescription_intelligence.medication.vocabulary import DRUG_TO_ALLERGEN_CLASSES
from app.modules.prescription_intelligence.provenance.evidence import EvidenceBuilder
from app.modules.prescription_intelligence.safety.duplicate_engine import RawMedicationInput
from app.modules.prescription_intelligence.safety.rules import (
    ALLERGY_RULES,
    AllergyRuleDefinition,
)
from app.modules.prescription_intelligence.safety.safety_validator import MedicationSafetyValidator


class AllergySafetyFinding(BaseModel):
    finding_type: str = "POTENTIAL_ALLERGY_CONCERN"
    severity: str = "HIGH"
    title: str
    description: str
    clinical_association: str
    evidence: Dict[str, Any]
    confidence: float = 1.0
    rule_id: str
    rule_version: str = "1.0.0"
    requires_review: bool = True


class AllergyEngine:
    """Evaluates medications against patient documented allergy list."""

    @classmethod
    def evaluate(
        cls,
        medications: List[RawMedicationInput],
        known_allergies: List[str],
        custom_rules: Optional[List[AllergyRuleDefinition]] = None,
    ) -> List[AllergySafetyFinding]:
        findings: List[AllergySafetyFinding] = []
        if not medications or not known_allergies:
            return findings

        rules = custom_rules if custom_rules is not None else ALLERGY_RULES
        normalized_allergies = [a.strip().lower() for a in known_allergies if isinstance(a, str) and a.strip()]

        for med in medications:
            if not med.canonical_medication_name or med.canonical_medication_name == "UNKNOWN":
                continue

            med_canonical = med.canonical_medication_name
            med_canonical_lower = med_canonical.lower()

            # 1. Check curated ALLERGY_RULES
            matched_rule = None
            for r in rules:
                if r.medication.lower() == med_canonical_lower:
                    if any(r.allergen_class.lower() in allergy or allergy in r.allergen_class.lower() for allergy in normalized_allergies):
                        matched_rule = r
                        break

            # 2. Check allergen class vocabulary mapping
            matched_allergen_class = None
            if not matched_rule and med_canonical in DRUG_TO_ALLERGEN_CLASSES:
                classes = DRUG_TO_ALLERGEN_CLASSES[med_canonical]
                for cls_name in classes:
                    for allergy in normalized_allergies:
                        if cls_name.lower() in allergy or allergy in cls_name.lower():
                            matched_allergen_class = cls_name
                            break
                    if matched_allergen_class:
                        break

            if matched_rule or matched_allergen_class:
                rule_id = matched_rule.rule_id if matched_rule else "ALLERGY-CLS-001"
                rule_version = matched_rule.rule_version if matched_rule else "1.0.0"
                source_ref = matched_rule.evidence_source if matched_rule else "Drug Class Allergen Cross-Reference"
                severity = matched_rule.severity if matched_rule else "HIGH"

                title = matched_rule.title if matched_rule else f"Potential Allergy Concern for {med_canonical}"
                matched_term = matched_rule.allergen_class if matched_rule else matched_allergen_class
                desc = (
                    f"Potential medication-allergy safety concern identified based on documented allergy record "
                    f"('{matched_term}'). Clinician review required."
                )
                assoc = "Prescription of a drug matching documented patient allergy requires clinical correlation."

                is_safe, violations = MedicationSafetyValidator.validate_safety_finding(title, desc, assoc)
                if not is_safe:
                    desc = "Potential medication-allergy safety concern identified based on documented allergy data. Clinician review required."

                evidence = EvidenceBuilder.build_evidence(
                    document_id=med.document_id,
                    prescription_id=med.prescription_id,
                    medication_id=med.id,
                    raw_medication_name=med.raw_medication_name,
                    canonical_medication_name=med_canonical,
                    source_text=med.source_text,
                    page_number=med.page_number,
                    rule_id=rule_id,
                    rule_version=rule_version,
                    source_reference=source_ref,
                    allergy_match=matched_term,
                    additional_context={"documented_allergies": known_allergies},
                )

                findings.append(
                    AllergySafetyFinding(
                        severity=severity,
                        title=title,
                        description=desc,
                        clinical_association=assoc,
                        evidence=evidence,
                        confidence=0.98,
                        rule_id=rule_id,
                        rule_version=rule_version,
                    )
                )

        return findings
