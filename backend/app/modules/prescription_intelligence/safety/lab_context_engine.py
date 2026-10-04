"""Lab-Medication Context Engine for NIDAN AI Phase 5.

Cross-references prescribed medications with relevant patient laboratory observations
(from Phase 3 / Phase 4 clinical observations and findings).

Strict Rule: Never autonomously concludes contraindication or commands drug cessation.
Surfaces non-alarmist observational clinical context connecting relevant lab values.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.modules.prescription_intelligence.provenance.evidence import EvidenceBuilder
from app.modules.prescription_intelligence.safety.duplicate_engine import RawMedicationInput
from app.modules.prescription_intelligence.safety.rules import (
    LAB_CONTEXT_RULES,
    LabContextRuleDefinition,
)
from app.modules.prescription_intelligence.safety.safety_validator import MedicationSafetyValidator


class RawLabObservationInput(BaseModel):
    id: str
    document_id: Optional[str] = None
    analyte: str
    canonical_name: str
    value: str
    normalized_value: Optional[float] = None
    unit: Optional[str] = None
    technical_status: str  # BELOW_REPORTED_RANGE, WITHIN_REPORTED_RANGE, ABOVE_REPORTED_RANGE, etc.
    finding_status: Optional[str] = None  # LOW, HIGH, CRITICAL_LOW, CRITICAL_HIGH, NORMAL
    observation_date: Optional[str] = None


class LabContextSafetyFinding(BaseModel):
    finding_type: str = "LAB_CONTEXT_SIGNAL"
    severity: str
    title: str
    description: str
    clinical_association: str
    evidence: Dict[str, Any]
    confidence: float = 1.0
    rule_id: str
    rule_version: str = "1.0.0"
    requires_review: bool = True


class LabContextEngine:
    """Connects recent abnormal lab observations to prescribed medications."""

    @classmethod
    def evaluate(
        cls,
        medications: List[RawMedicationInput],
        observations: List[RawLabObservationInput],
        custom_rules: Optional[List[LabContextRuleDefinition]] = None,
    ) -> List[LabContextSafetyFinding]:
        findings: List[LabContextSafetyFinding] = []
        if not medications or not observations:
            return findings

        rules = custom_rules if custom_rules is not None else LAB_CONTEXT_RULES

        for med in medications:
            if not med.canonical_medication_name or med.canonical_medication_name == "UNKNOWN":
                continue

            med_canonical = med.canonical_medication_name
            med_canonical_lower = med_canonical.lower()

            for rule in rules:
                if rule.medication.lower() != med_canonical_lower:
                    continue

                # Look for matching lab observation
                for obs in observations:
                    obs_name_lower = obs.canonical_name.lower()
                    rule_analyte_lower = rule.lab_analyte.lower()

                    if rule_analyte_lower in obs_name_lower or obs_name_lower in rule_analyte_lower:
                        # Check status match
                        status_str = (obs.finding_status or obs.technical_status or "").upper()
                        is_match = False

                        if rule.condition_status == "HIGH" and any(k in status_str for k in ["HIGH", "ABOVE"]):
                            is_match = True
                        elif rule.condition_status == "LOW" and any(k in status_str for k in ["LOW", "BELOW"]):
                            is_match = True
                        elif rule.condition_status in ["ABNORMAL", "CRITICAL"] and any(k in status_str for k in ["HIGH", "LOW", "CRITICAL", "ABOVE", "BELOW"]):
                            is_match = True

                        if is_match:
                            # Build finding
                            title = rule.title
                            desc = rule.description
                            assoc = rule.clinical_association

                            is_safe, violations = MedicationSafetyValidator.validate_safety_finding(title, desc, assoc)
                            if not is_safe:
                                desc = f"Recent laboratory observation ({obs.canonical_name}) may be relevant to medication review for {med_canonical}. Clinical correlation recommended."

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
                                lab_observation_id=obs.id,
                                lab_analyte=obs.canonical_name,
                                lab_value=f"{obs.value} {obs.unit or ''}".strip(),
                                lab_date=obs.observation_date,
                                lab_status=status_str,
                                additional_context={"matched_analyte": obs.canonical_name, "raw_status": status_str},
                            )

                            findings.append(
                                LabContextSafetyFinding(
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
                            # Single match per rule/medication is sufficient
                            break

        return findings
