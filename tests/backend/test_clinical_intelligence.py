import pytest
from datetime import date, datetime, timezone
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.patients.models import Patient
from app.modules.medical_documents.models import (
    MedicalDocument,
    DocumentExtraction,
    DocumentExtractionEntity,
)
from app.modules.clinical_intelligence.models import (
    ClinicalAnalysis,
    ClinicalFinding,
    FindingTypeEnum,
    FindingStatusEnum,
    FindingSeverityEnum,
    FindingReviewStatusEnum,
)
from app.modules.clinical_intelligence.reference_ranges.resolver import ReferenceRangeResolver
from app.modules.clinical_intelligence.rules.abnormality import LabAbnormalityRule
from app.modules.clinical_intelligence.rules.critical import CriticalValueRule
from app.modules.clinical_intelligence.rules.deficiency import DeficiencyDetectionRule
from app.modules.clinical_intelligence.rules.patterns import MultiMarkerPatternRule
from app.modules.clinical_intelligence.engine.safety_validator import SafetyValidator
from app.modules.clinical_intelligence.service import ClinicalIntelligenceService
from app.core.security import create_access_token, UserRole


@pytest.fixture
async def sample_patient(db_session: AsyncSession) -> Patient:
    patient = Patient(
        id=str(uuid.uuid4()),
        mrn=f"MRN-{uuid.uuid4().hex[:8].upper()}",
        first_name="Jane",
        last_name="Doe",
        gender="female",
        date_of_birth=date(1995, 5, 20),
        phone="+15551234567",
        email="jane.doe@example.com",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest.fixture
async def sample_document(db_session: AsyncSession, sample_patient: Patient) -> MedicalDocument:
    doc = MedicalDocument(
        id=str(uuid.uuid4()),
        patient_id=sample_patient.id,
        original_filename="cbc_report.pdf",
        stored_filename="cbc_report.pdf",
        mime_type="application/pdf",
        document_type="BLOOD_REPORT",
        file_size=10240,
        sha256_hash="test_sha256",
        storage_key="test/cbc.pdf",
        processing_status="COMPLETED",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest.fixture
async def sample_extraction(db_session: AsyncSession, sample_document: MedicalDocument) -> DocumentExtraction:
    extraction = DocumentExtraction(
        id=str(uuid.uuid4()),
        document_id=sample_document.id,
        extraction_version=1,
        provider="local_pdf",
        provider_version="1.0.0",
        status="COMPLETED",
        raw_text="Hemoglobin: 9.8 g/dL (12.0 - 16.0)\nMCV: 72.0 fL (80.0 - 96.0)\nFerritin: 12.0 ng/mL (30.0 - 200.0)",
    )
    db_session.add(extraction)
    await db_session.commit()
    await db_session.refresh(extraction)

    entities = [
        DocumentExtractionEntity(
            id=str(uuid.uuid4()),
            extraction_id=extraction.id,
            document_id=sample_document.id,
            raw_name="Hemoglobin",
            canonical_name="Hemoglobin",
            value_text="9.8",
            numeric_value=9.8,
            original_unit="g/dL",
            normalized_unit="g/dL",
            reference_range_text="12.0 - 16.0",
            reference_min=12.0,
            reference_max=16.0,
            technical_status="BELOW_REPORTED_RANGE",
            confidence=0.96,
            page_number=1,
            review_status="PENDING",
        ),
        DocumentExtractionEntity(
            id=str(uuid.uuid4()),
            extraction_id=extraction.id,
            document_id=sample_document.id,
            raw_name="MCV",
            canonical_name="MCV",
            value_text="72.0",
            numeric_value=72.0,
            original_unit="fL",
            normalized_unit="fL",
            reference_range_text="80.0 - 96.0",
            reference_min=80.0,
            reference_max=96.0,
            technical_status="BELOW_REPORTED_RANGE",
            confidence=0.94,
            page_number=1,
            review_status="PENDING",
        ),
        DocumentExtractionEntity(
            id=str(uuid.uuid4()),
            extraction_id=extraction.id,
            document_id=sample_document.id,
            raw_name="Ferritin",
            canonical_name="Ferritin",
            value_text="12.0",
            numeric_value=12.0,
            original_unit="ng/mL",
            normalized_unit="ng/mL",
            reference_range_text="30.0 - 200.0",
            reference_min=30.0,
            reference_max=200.0,
            technical_status="BELOW_REPORTED_RANGE",
            confidence=0.92,
            page_number=1,
            review_status="PENDING",
        ),
    ]
    for e in entities:
        db_session.add(e)
    await db_session.commit()

    return extraction


@pytest.mark.asyncio
async def test_reference_range_demographic_resolution():
    resolver = ReferenceRangeResolver()
    
    # Male resolution from knowledge base
    ent_male = DocumentExtractionEntity(
        id="e_m", extraction_id="ext", document_id="doc",
        raw_name="Hemoglobin", canonical_name="Hemoglobin",
        value_text="15.0", numeric_value=15.0, original_unit="g/dL", normalized_unit="g/dL",
        confidence=0.95
    )
    resolved_m = resolver.resolve(ent_male, patient_sex="male", patient_age=30.0)
    assert resolved_m.is_resolved is True
    assert resolved_m.source_type == "KNOWLEDGE_BASE"
    assert resolved_m.lower_bound == 13.0
    assert resolved_m.upper_bound == 17.5

    # Female resolution from knowledge base
    ent_female = DocumentExtractionEntity(
        id="e_f", extraction_id="ext", document_id="doc",
        raw_name="Hemoglobin", canonical_name="Hemoglobin",
        value_text="14.0", numeric_value=14.0, original_unit="g/dL", normalized_unit="g/dL",
        confidence=0.95
    )
    resolved_f = resolver.resolve(ent_female, patient_sex="female", patient_age=30.0)
    assert resolved_f.is_resolved is True
    assert resolved_f.lower_bound == 12.0
    assert resolved_f.upper_bound == 16.0


@pytest.mark.asyncio
async def test_reference_range_priority():
    resolver = ReferenceRangeResolver()
    
    # Report-provided should take priority over knowledge base
    ent_report = DocumentExtractionEntity(
        id="e_rep", extraction_id="ext", document_id="doc",
        raw_name="Hemoglobin", canonical_name="Hemoglobin",
        value_text="14.0", numeric_value=14.0, original_unit="g/dL", normalized_unit="g/dL",
        reference_min=11.5, reference_max=15.5,
        confidence=0.95
    )
    resolved = resolver.resolve(ent_report, patient_sex="male", patient_age=30.0)
    assert resolved.source_type == "REPORT"
    assert resolved.lower_bound == 11.5
    assert resolved.upper_bound == 15.5


@pytest.mark.asyncio
async def test_safety_validator_guardrails():
    # Dangerous autonomous diagnosis
    res1 = SafetyValidator.validate_text("You have diabetes mellitus.")
    assert res1.is_safe is False
    assert len(res1.violations) > 0

    # Dangerous medication prescription
    res2 = SafetyValidator.validate_text("You should take iron supplements 65mg daily.")
    assert res2.is_safe is False

    # Safe CDSS advisory phrasing
    res3 = SafetyValidator.validate_text("Finding may be associated with iron deficiency; clinical correlation recommended.")
    assert res3.is_safe is True
    assert len(res3.violations) == 0


@pytest.mark.asyncio
async def test_clinical_analysis_execution_and_findings(
    db_session: AsyncSession,
    sample_document: MedicalDocument,
    sample_extraction: DocumentExtraction,
):
    service = ClinicalIntelligenceService(db_session)
    analysis = await service.run_clinical_analysis(
        document_id=sample_document.id,
        force_reanalyze=True,
    )

    assert analysis is not None
    assert analysis.document_id == sample_document.id
    assert analysis.status == "COMPLETED"
    assert analysis.findings_count > 0
    assert analysis.abnormal_count >= 3
    assert analysis.pattern_count >= 1

    # Verify Iron Pattern Finding
    iron_pattern = next((f for f in analysis.findings if f.rule_id == "IRON_PATTERN_001"), None)
    assert iron_pattern is not None
    assert iron_pattern.finding_type == FindingTypeEnum.PATTERN.value
    assert "iron deficiency" in iron_pattern.clinical_association.lower()
    assert len(iron_pattern.evidence) >= 2


@pytest.mark.asyncio
async def test_clinical_analysis_idempotency(
    db_session: AsyncSession,
    sample_document: MedicalDocument,
    sample_extraction: DocumentExtraction,
):
    service = ClinicalIntelligenceService(db_session)
    analysis1 = await service.run_clinical_analysis(document_id=sample_document.id)
    analysis2 = await service.run_clinical_analysis(document_id=sample_document.id)

    # Must return exact same analysis without duplicating records
    assert analysis1.id == analysis2.id
    assert analysis1.analysis_version == analysis2.analysis_version


@pytest.mark.asyncio
async def test_doctor_review_workflow(
    db_session: AsyncSession,
    sample_document: MedicalDocument,
    sample_extraction: DocumentExtraction,
):
    service = ClinicalIntelligenceService(db_session)
    analysis = await service.run_clinical_analysis(document_id=sample_document.id, force_reanalyze=True)
    first_finding = analysis.findings[0]

    from app.modules.clinical_intelligence.schemas import FindingReviewRequest

    # Review accept
    reviewed = await service.review_finding(
        finding_id=first_finding.id,
        review_data=FindingReviewRequest(
            review_status=FindingReviewStatusEnum.ACCEPTED,
            reviewer_notes="Verified against blood film microscopy.",
        ),
        reviewer_id="doc_123",
    )
    assert reviewed.review_status == "ACCEPTED"
    assert reviewed.reviewed_by == "doc_123"
    assert reviewed.reviewer_notes == "Verified against blood film microscopy."


@pytest.mark.asyncio
async def test_api_clinical_endpoints(
    client: AsyncClient,
    sample_document: MedicalDocument,
    sample_extraction: DocumentExtraction,
):
    # 1. Trigger Analysis via POST
    res_post = await client.post(f"/api/v1/medical-documents/{sample_document.id}/clinical-analysis")
    assert res_post.status_code == 200
    data = res_post.json()
    assert data["document_id"] == sample_document.id
    assert "findings" in data
    assert len(data["findings"]) > 0

    # 2. Get Analysis via GET
    res_get = await client.get(f"/api/v1/medical-documents/{sample_document.id}/clinical-analysis")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == data["id"]

    # 3. List Findings
    res_find = await client.get(f"/api/v1/medical-documents/{sample_document.id}/clinical-findings")
    assert res_find.status_code == 200
    assert len(res_find.json()) > 0

    # 4. Patient Longitudinal Findings
    res_long = await client.get(f"/api/v1/patients/{sample_document.patient_id}/clinical-findings")
    assert res_long.status_code == 200
    long_data = res_long.json()
    assert long_data["patient_id"] == sample_document.patient_id
    assert "analytes" in long_data
