from typing import List, Optional
import uuid
from app.modules.clinical_intelligence.models import (
    ClinicalFinding,
    FindingReviewStatusEnum,
)
from app.modules.clinical_intelligence.rules.base import RuleEvaluationResult
from app.modules.clinical_intelligence.engine.safety_validator import SafetyValidator


class FindingBuilder:
    @staticmethod
    def build_finding(
        result: RuleEvaluationResult,
        analysis_id: str,
        patient_id: str,
        document_id: str,
        extraction_id: str,
        entity_id: Optional[str] = None,
    ) -> ClinicalFinding:
        # Run safety validation
        is_safe, violations = SafetyValidator.validate_finding(
            title=result.title,
            explanation=result.explanation,
            clinical_association=result.clinical_association,
        )

        if not is_safe:
            # Fallback to sanitized safe description
            title = f"Finding for {result.analyte or 'Analyte'} requires clinician correlation"
            explanation = "Automated clinical finding language was adjusted to maintain non-diagnostic CDSS compliance."
            clinical_association = "Clinical correlation recommended."
        else:
            title = result.title
            explanation = result.explanation
            clinical_association = result.clinical_association

        finding = ClinicalFinding(
            id=str(uuid.uuid4()),
            analysis_id=analysis_id,
            patient_id=patient_id,
            document_id=document_id,
            extraction_id=extraction_id,
            entity_id=entity_id,
            finding_type=result.finding_type,
            analyte=result.analyte,
            value=result.value,
            normalized_value=result.normalized_value,
            unit=result.unit,
            status=result.status,
            severity=result.severity,
            title=title,
            explanation=explanation,
            clinical_association=clinical_association,
            evidence=result.evidence,
            confidence=result.confidence,
            rule_id=result.rule_id,
            rule_version=result.rule_version,
            reference_source=result.reference_source,
            reference_source_version=result.reference_source_version,
            requires_review=result.requires_review,
            review_status=FindingReviewStatusEnum.PENDING.value,
        )
        return finding
