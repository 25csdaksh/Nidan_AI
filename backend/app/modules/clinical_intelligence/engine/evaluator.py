from datetime import date, datetime
from typing import Any, Dict, List, Optional
from app.modules.patients.models import Patient
from app.modules.medical_documents.models import (
    MedicalDocument,
    DocumentExtraction,
    DocumentExtractionEntity,
)
from app.modules.clinical_intelligence.reference_ranges.resolver import ReferenceRangeResolver


class ClinicalEvaluationContextBuilder:
    def __init__(self, resolver: Optional[ReferenceRangeResolver] = None):
        self.resolver = resolver or ReferenceRangeResolver()

    def build_context(
        self,
        document: MedicalDocument,
        extraction: DocumentExtraction,
        entities: List[DocumentExtractionEntity],
        patient: Optional[Patient] = None,
    ) -> Dict[str, Any]:
        patient_sex = None
        patient_age = None
        pregnancy_status = "all"

        if patient:
            if patient.gender:
                patient_sex = patient.gender.lower()
            if patient.date_of_birth:
                today = date.today()
                dob = patient.date_of_birth
                patient_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        entity_evaluations = []
        for ent in entities:
            # Skip rejected entities from clinical evaluation
            if ent.review_status == "REJECTED":
                continue

            resolved_range = self.resolver.resolve(
                entity=ent,
                patient_sex=patient_sex,
                patient_age=patient_age,
                pregnancy_status=pregnancy_status,
            )

            entity_evaluations.append({
                "entity": ent,
                "resolved_range": resolved_range,
            })

        return {
            "document": document,
            "extraction": extraction,
            "patient": patient,
            "patient_sex": patient_sex,
            "patient_age": patient_age,
            "pregnancy_status": pregnancy_status,
            "entity_evaluations": entity_evaluations,
        }
