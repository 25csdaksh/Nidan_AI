"""Evidence Provenance Builder for Prescription Intelligence Findings.

Ensures every extracted medication and safety alert contains traceable links:
- Document ID
- Prescription ID
- Medication ID
- Page Number
- Bounding Box
- Source Text
- Lab Observation ID
- Clinical Finding ID
- Allergy Record
- Rule ID & Rule Version
- Source Reference Citation
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MedicationEvidence(BaseModel):
    document_id: Optional[str] = None
    prescription_id: Optional[str] = None
    medication_id: Optional[str] = None
    raw_medication_name: Optional[str] = None
    canonical_medication_name: Optional[str] = None
    source_text: Optional[str] = None
    page_number: int = 1
    bounding_box: Optional[dict] = None
    rule_id: Optional[str] = None
    rule_version: str = "1.0.0"
    source_reference: Optional[str] = None
    lab_observation_id: Optional[str] = None
    lab_analyte: Optional[str] = None
    lab_value: Optional[str] = None
    lab_date: Optional[str] = None
    lab_status: Optional[str] = None
    allergy_match: Optional[str] = None
    additional_context: Dict[str, Any] = Field(default_factory=dict)


class EvidenceBuilder:
    """Helper to assemble structured provenance JSON payloads."""

    @classmethod
    def build_evidence(
        cls,
        document_id: Optional[str] = None,
        prescription_id: Optional[str] = None,
        medication_id: Optional[str] = None,
        raw_medication_name: Optional[str] = None,
        canonical_medication_name: Optional[str] = None,
        source_text: Optional[str] = None,
        page_number: int = 1,
        bounding_box: Optional[dict] = None,
        rule_id: Optional[str] = None,
        rule_version: str = "1.0.0",
        source_reference: Optional[str] = None,
        lab_observation_id: Optional[str] = None,
        lab_analyte: Optional[str] = None,
        lab_value: Optional[str] = None,
        lab_date: Optional[str] = None,
        lab_status: Optional[str] = None,
        allergy_match: Optional[str] = None,
        additional_context: Optional[dict] = None,
    ) -> Dict[str, Any]:
        ev = MedicationEvidence(
            document_id=document_id,
            prescription_id=prescription_id,
            medication_id=medication_id,
            raw_medication_name=raw_medication_name,
            canonical_medication_name=canonical_medication_name,
            source_text=source_text,
            page_number=page_number,
            bounding_box=bounding_box,
            rule_id=rule_id,
            rule_version=rule_version,
            source_reference=source_reference,
            lab_observation_id=lab_observation_id,
            lab_analyte=lab_analyte,
            lab_value=lab_value,
            lab_date=lab_date,
            lab_status=lab_status,
            allergy_match=allergy_match,
            additional_context=additional_context or {},
        )
        return ev.model_dump()
