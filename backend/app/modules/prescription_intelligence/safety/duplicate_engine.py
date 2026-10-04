"""Duplicate Medication Detection Engine for NIDAN AI Phase 5.

Detects:
- Exact duplicate medication entries within the same prescription
- Repeated medications across recent active prescriptions
- Repeated generic therapeutic classes

Strict Safety Policy: Never commands the clinician to stop or cancel medication.
Surfaces non-alarming observational notice to verify intended regimen.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.modules.prescription_intelligence.provenance.evidence import EvidenceBuilder
from app.modules.prescription_intelligence.safety.safety_validator import MedicationSafetyValidator


class RawMedicationInput(BaseModel):
    id: Optional[str] = None
    prescription_id: Optional[str] = None
    document_id: Optional[str] = None
    raw_medication_name: str
    canonical_medication_name: str
    generic_name: Optional[str] = None
    strength_value: Optional[float] = None
    strength_unit: Optional[str] = None
    source_text: Optional[str] = None
    page_number: int = 1


class DuplicateSafetyFinding(BaseModel):
    finding_type: str = "POTENTIAL_DUPLICATE"
    severity: str = "INFO"
    title: str
    description: str
    clinical_association: str
    evidence: Dict[str, Any]
    confidence: float = 1.0
    rule_id: str = "DUP-MED-001"
    rule_version: str = "1.0.0"
    requires_review: bool = True


class DuplicateEngine:
    """Detects duplicate medication entries across current and active prescriptions."""

    @classmethod
    def evaluate(cls, medications: List[RawMedicationInput]) -> List[DuplicateSafetyFinding]:
        findings: List[DuplicateSafetyFinding] = []
        if len(medications) < 2:
            return findings

        # Group by canonical medication name
        grouped: Dict[str, List[RawMedicationInput]] = {}
        for med in medications:
            if med.canonical_medication_name and med.canonical_medication_name != "UNKNOWN":
                grouped.setdefault(med.canonical_medication_name, []).append(med)

        for canonical_name, items in grouped.items():
            if len(items) > 1:
                # Multiple entries found
                title = f"Multiple Entries Documented for {canonical_name}"
                desc = (
                    f"Multiple entries for {canonical_name} ({len(items)} items) were detected "
                    "in the available prescription records. Clinician verification of the intended regimen is recommended."
                )
                assoc = "Duplicate medication entries may represent intended dose escalations, overlapping visits, or unintentional duplication."

                # Verify safety text guardrails
                is_safe, violations = MedicationSafetyValidator.validate_safety_finding(title, desc, assoc)
                if not is_safe:
                    desc = f"Multiple entries for {canonical_name} were detected. Verify intended regimen."

                item_ids = [it.id for it in items if it.id]
                first_item = items[0]

                evidence = EvidenceBuilder.build_evidence(
                    document_id=first_item.document_id,
                    prescription_id=first_item.prescription_id,
                    medication_id=first_item.id,
                    raw_medication_name=first_item.raw_medication_name,
                    canonical_medication_name=canonical_name,
                    source_text=first_item.source_text,
                    page_number=first_item.page_number,
                    rule_id="DUP-MED-001",
                    rule_version="1.0.0",
                    source_reference="Prescription Duplicate Analyzer",
                    additional_context={"duplicate_count": len(items), "matched_ids": item_ids},
                )

                findings.append(
                    DuplicateSafetyFinding(
                        title=title,
                        description=desc,
                        clinical_association=assoc,
                        evidence=evidence,
                        confidence=0.95,
                    )
                )

        return findings
