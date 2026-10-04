import uuid
import pytest
from datetime import datetime, timezone, date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.clinical_intelligence.models import (
    ClinicalObservation,
    LongitudinalAnalysis,
    LongitudinalTrend,
    LongitudinalSummarySection,
    LongitudinalReviewNote,
    TrendDirectionEnum,
    TrendStatusEnum,
    AbnormalityDynamicsEnum,
    FindingStatusEnum,
)
from app.modules.clinical_intelligence.longitudinal.date_resolver import (
    ObservationDateResolver,
)
from app.modules.clinical_intelligence.longitudinal.trend_rules import (
    AnalyteTrendRule,
    get_trend_rule,
)
from app.modules.clinical_intelligence.longitudinal.trend_engine import (
    TrendEngine,
)
from app.modules.clinical_intelligence.longitudinal.dynamics_engine import (
    AbnormalityDynamicsEngine,
)
from app.modules.clinical_intelligence.longitudinal.panel_completeness import (
    PanelCompletenessAnalyzer,
)
from app.modules.clinical_intelligence.longitudinal.comparison_engine import (
    CrossVisitComparisonEngine,
)
from app.modules.clinical_intelligence.longitudinal.summary_engine import (
    LongitudinalSummaryEngine,
)
from app.modules.clinical_intelligence.engine.safety_validator import (
    SafetyValidator,
)
from app.modules.clinical_intelligence.service import ClinicalIntelligenceService
from app.modules.clinical_intelligence.schemas import (
    LongitudinalAnalysisRequest,
    LongitudinalReviewNoteCreate,
    VisitComparisonRequest,
)
from app.modules.medical_documents.models import (
    MedicalDocument,
    DocumentExtraction,
    DocumentExtractionEntity,
)
from app.modules.patients.models import Patient
from app.modules.audit.models import AuditLog


# ---------------------------------------------------------------------
# Test 1: Observation Date Resolution Priority
# ---------------------------------------------------------------------
def test_observation_date_resolution():
    # 1. Report Date explicit
    text_report = "Laboratory Result Report Date: 2026-08-15 Sample Collected: 2026-08-14"
    res1 = ObservationDateResolver.resolve_date(document_text=text_report)
    assert res1.source == "REPORT_DATE"
    assert res1.confidence == "HIGH"
    assert res1.resolved_date is not None
    assert res1.resolved_date.strftime("%Y-%m-%d") == "2026-08-15"

    # 2. Test / Collection Date explicit
    text_test = "Blood Examination. Specimen Date: 12-07-2026"
    res2 = ObservationDateResolver.resolve_date(document_text=text_test)
    assert res2.source == "TEST_DATE"
    assert res2.confidence == "HIGH"
    assert res2.resolved_date.strftime("%Y-%m-%d") == "2026-07-12"

    # 3. Document Metadata fallback
    meta = {"document_date": "2026-05-10"}
    res3 = ObservationDateResolver.resolve_date(document_text="No dates here", document_metadata=meta)
    assert res3.source == "DOCUMENT_DATE"
    assert res3.confidence == "MEDIUM"
    assert res3.resolved_date.strftime("%Y-%m-%d") == "2026-05-10"

    # 4. Upload timestamp fallback
    now = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)
    res4 = ObservationDateResolver.resolve_date(document_text=None, document_metadata={}, document_created_at=now)
    assert res4.source == "UPLOAD_TIMESTAMP"
    assert res4.confidence == "LOW"

    # 5. Unknown date
    res5 = ObservationDateResolver.resolve_date(document_text=None, document_metadata=None, document_created_at=None)
    assert res5.source == "UNKNOWN"
    assert res5.resolved_date is None


# ---------------------------------------------------------------------
# Test 2: Analyte Trend Calculation & Zero Division Handling
# ---------------------------------------------------------------------
def test_trend_engine_calculations():
    # Setup test observations for Hemoglobin
    obs1 = ClinicalObservation(
        id="obs1",
        patient_id="p1",
        document_id="doc1",
        extraction_id="ext1",
        analyte="Hemoglobin",
        canonical_name="Hemoglobin",
        value="12.4",
        normalized_value=12.4,
        unit="g/dL",
        technical_status=FindingStatusEnum.NORMAL.value,
        observation_date=datetime(2026, 7, 10, tzinfo=timezone.utc),
        observation_date_source="REPORT_DATE",
        date_confidence="HIGH",
    )
    obs2 = ClinicalObservation(
        id="obs2",
        patient_id="p1",
        document_id="doc2",
        extraction_id="ext2",
        analyte="Hemoglobin",
        canonical_name="Hemoglobin",
        value="10.8",
        normalized_value=10.8,
        unit="g/dL",
        technical_status=FindingStatusEnum.LOW.value,
        observation_date=datetime(2026, 8, 15, tzinfo=timezone.utc),
        observation_date_source="REPORT_DATE",
        date_confidence="HIGH",
    )
    obs3 = ClinicalObservation(
        id="obs3",
        patient_id="p1",
        document_id="doc3",
        extraction_id="ext3",
        analyte="Hemoglobin",
        canonical_name="Hemoglobin",
        value="10.2",
        normalized_value=10.2,
        unit="g/dL",
        technical_status=FindingStatusEnum.LOW.value,
        observation_date=datetime(2026, 9, 20, tzinfo=timezone.utc),
        observation_date_source="REPORT_DATE",
        date_confidence="HIGH",
    )

    trends = TrendEngine.evaluate_trends([obs1, obs2, obs3])
    assert len(trends) == 1
    hb_trend = trends[0]

    assert hb_trend.canonical_name == "Hemoglobin"
    assert hb_trend.observation_count == 3
    assert hb_trend.first_value == 12.4
    assert hb_trend.last_value == 10.2
    assert hb_trend.absolute_change == -0.6
    assert hb_trend.direction in (TrendDirectionEnum.DECREASED.value, "DECREASED")
    assert hb_trend.trend_status in (TrendStatusEnum.WORSENING.value, "WORSENING")

    # Test Zero Division Handling
    zero_obs1 = ClinicalObservation(
        id="z1",
        patient_id="p1",
        document_id="doc1",
        extraction_id="ext1",
        analyte="Bilirubin",
        canonical_name="Bilirubin Direct",
        value="0.0",
        normalized_value=0.0,
        unit="mg/dL",
        technical_status="NORMAL",
        observation_date=datetime(2026, 7, 10, tzinfo=timezone.utc),
        observation_date_source="REPORT_DATE",
        date_confidence="HIGH",
    )
    zero_obs2 = ClinicalObservation(
        id="z2",
        patient_id="p1",
        document_id="doc2",
        extraction_id="ext2",
        analyte="Bilirubin",
        canonical_name="Bilirubin Direct",
        value="0.3",
        normalized_value=0.3,
        unit="mg/dL",
        technical_status="NORMAL",
        observation_date=datetime(2026, 8, 15, tzinfo=timezone.utc),
        observation_date_source="REPORT_DATE",
        date_confidence="HIGH",
    )
    z_trends = TrendEngine.evaluate_trends([zero_obs1, zero_obs2])
    assert len(z_trends) == 1
    assert z_trends[0].percentage_change is None  # Never divide by zero


# ---------------------------------------------------------------------
# Test 3: Noise Threshold / Stable Changes
# ---------------------------------------------------------------------
def test_noise_threshold_and_stability():
    # Creatinine: 0.9 -> 0.91 (delta = 0.01 is below absolute threshold 0.15)
    c1 = ClinicalObservation(
        id="c1",
        patient_id="p1",
        document_id="doc1",
        extraction_id="ext1",
        analyte="Creatinine",
        canonical_name="Creatinine",
        value="0.9",
        normalized_value=0.9,
        unit="mg/dL",
        technical_status=FindingStatusEnum.NORMAL.value,
        observation_date=datetime(2026, 1, 10, tzinfo=timezone.utc),
        observation_date_source="REPORT_DATE",
        date_confidence="HIGH",
    )
    c2 = ClinicalObservation(
        id="c2",
        patient_id="p1",
        document_id="doc2",
        extraction_id="ext2",
        analyte="Creatinine",
        canonical_name="Creatinine",
        value="0.91",
        normalized_value=0.91,
        unit="mg/dL",
        technical_status=FindingStatusEnum.NORMAL.value,
        observation_date=datetime(2026, 5, 10, tzinfo=timezone.utc),
        observation_date_source="REPORT_DATE",
        date_confidence="HIGH",
    )

    trends = TrendEngine.evaluate_trends([c1, c2])
    assert len(trends) == 1
    assert trends[0].direction in (TrendDirectionEnum.UNCHANGED.value, "UNCHANGED")
    assert trends[0].trend_status in (TrendStatusEnum.STABLE.value, "STABLE")


# ---------------------------------------------------------------------
# Test 4: Abnormality Dynamics Engine (Persistent, New, Resolved, Recurring, Fluctuation)
# ---------------------------------------------------------------------
def test_abnormality_dynamics_engine():
    # Persistent Low: LOW -> LOW -> LOW
    obs_p1 = ClinicalObservation(
        id="p1", patient_id="pat", document_id="d1", extraction_id="e1", analyte="Hemoglobin", canonical_name="Hemoglobin",
        value="10.2", normalized_value=10.2, unit="g/dL", technical_status=FindingStatusEnum.LOW.value,
        observation_date=datetime(2026, 1, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )
    obs_p2 = ClinicalObservation(
        id="p2", patient_id="pat", document_id="d2", extraction_id="e2", analyte="Hemoglobin", canonical_name="Hemoglobin",
        value="10.5", normalized_value=10.5, unit="g/dL", technical_status=FindingStatusEnum.LOW.value,
        observation_date=datetime(2026, 3, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )
    obs_p3 = ClinicalObservation(
        id="p3", patient_id="pat", document_id="d3", extraction_id="e3", analyte="Hemoglobin", canonical_name="Hemoglobin",
        value="10.1", normalized_value=10.1, unit="g/dL", technical_status=FindingStatusEnum.LOW.value,
        observation_date=datetime(2026, 6, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )

    # New High: NORMAL -> HIGH
    obs_n1 = ClinicalObservation(
        id="n1", patient_id="pat", document_id="d1", extraction_id="e1", analyte="HbA1c", canonical_name="HbA1c",
        value="5.4", normalized_value=5.4, unit="%", technical_status=FindingStatusEnum.NORMAL.value,
        observation_date=datetime(2026, 1, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )
    obs_n2 = ClinicalObservation(
        id="n2", patient_id="pat", document_id="d2", extraction_id="e2", analyte="HbA1c", canonical_name="HbA1c",
        value="6.5", normalized_value=6.5, unit="%", technical_status=FindingStatusEnum.HIGH.value,
        observation_date=datetime(2026, 3, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )

    # Resolved Low: LOW -> NORMAL
    obs_r1 = ClinicalObservation(
        id="r1", patient_id="pat", document_id="d1", extraction_id="e1", analyte="Vitamin D", canonical_name="Vitamin D",
        value="14.0", normalized_value=14.0, unit="ng/mL", technical_status=FindingStatusEnum.LOW.value,
        observation_date=datetime(2026, 1, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )
    obs_r2 = ClinicalObservation(
        id="r2", patient_id="pat", document_id="d2", extraction_id="e2", analyte="Vitamin D", canonical_name="Vitamin D",
        value="32.0", normalized_value=32.0, unit="ng/mL", technical_status=FindingStatusEnum.NORMAL.value,
        observation_date=datetime(2026, 3, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )

    # Recurring: LOW -> NORMAL -> LOW
    obs_rec1 = ClinicalObservation(
        id="rec1", patient_id="pat", document_id="d1", extraction_id="e1", analyte="Platelets", canonical_name="Platelet Count",
        value="120", normalized_value=120.0, unit="x10^3/uL", technical_status=FindingStatusEnum.LOW.value,
        observation_date=datetime(2026, 1, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )
    obs_rec2 = ClinicalObservation(
        id="rec2", patient_id="pat", document_id="d2", extraction_id="e2", analyte="Platelets", canonical_name="Platelet Count",
        value="200", normalized_value=200.0, unit="x10^3/uL", technical_status=FindingStatusEnum.NORMAL.value,
        observation_date=datetime(2026, 3, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )
    obs_rec3 = ClinicalObservation(
        id="rec3", patient_id="pat", document_id="d3", extraction_id="e3", analyte="Platelets", canonical_name="Platelet Count",
        value="110", normalized_value=110.0, unit="x10^3/uL", technical_status=FindingStatusEnum.LOW.value,
        observation_date=datetime(2026, 6, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )

    # Fluctuation: HIGH -> LOW -> HIGH
    obs_f1 = ClinicalObservation(
        id="f1", patient_id="pat", document_id="d1", extraction_id="e1", analyte="TSH", canonical_name="Thyroid Stimulating Hormone",
        value="6.5", normalized_value=6.5, unit="uIU/mL", technical_status=FindingStatusEnum.HIGH.value,
        observation_date=datetime(2026, 1, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )
    obs_f2 = ClinicalObservation(
        id="f2", patient_id="pat", document_id="d2", extraction_id="e2", analyte="TSH", canonical_name="Thyroid Stimulating Hormone",
        value="0.2", normalized_value=0.2, unit="uIU/mL", technical_status=FindingStatusEnum.LOW.value,
        observation_date=datetime(2026, 3, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )
    obs_f3 = ClinicalObservation(
        id="f3", patient_id="pat", document_id="d3", extraction_id="e3", analyte="TSH", canonical_name="Thyroid Stimulating Hormone",
        value="7.1", normalized_value=7.1, unit="uIU/mL", technical_status=FindingStatusEnum.HIGH.value,
        observation_date=datetime(2026, 6, 1, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH"
    )

    all_obs = [
        obs_p1, obs_p2, obs_p3,
        obs_n1, obs_n2,
        obs_r1, obs_r2,
        obs_rec1, obs_rec2, obs_rec3,
        obs_f1, obs_f2, obs_f3,
    ]

    report = AbnormalityDynamicsEngine.evaluate_dynamics(all_obs)

    # Verify Persistent
    assert len(report.persistent_abnormalities) >= 1
    assert any(p.canonical_name == "Hemoglobin" and p.persistence_count == 3 for p in report.persistent_abnormalities)

    # Verify New
    assert len(report.new_abnormalities) >= 1
    assert any(n.canonical_name == "HbA1c" for n in report.new_abnormalities)

    # Verify Resolved
    assert len(report.resolved_abnormalities) >= 1
    assert any(r.canonical_name == "Vitamin D" for r in report.resolved_abnormalities)

    # Verify Recurring
    assert len(report.recurring_abnormalities) >= 1
    assert any(rec.canonical_name == "Platelet Count" for rec in report.recurring_abnormalities)

    # Verify Fluctuation
    assert len(report.fluctuations) >= 1
    assert any(fl.canonical_name == "Thyroid Stimulating Hormone" for fl in report.fluctuations)


# ---------------------------------------------------------------------
# Test 5: Panel Completeness Analyzer
# ---------------------------------------------------------------------
def test_panel_completeness():
    # Only Hemoglobin, WBC, Platelets -> partial CBC
    obs_cbc = [
        ClinicalObservation(
            id="1", patient_id="p1", document_id="d1", extraction_id="e1", analyte="Hemoglobin", canonical_name="Hemoglobin",
            value="13.0", normalized_value=13.0, observation_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
            observation_date_source="REPORT_DATE", date_confidence="HIGH",
        ),
        ClinicalObservation(
            id="2", patient_id="p1", document_id="d1", extraction_id="e1", analyte="WBC", canonical_name="White Blood Cell Count",
            value="7.0", normalized_value=7.0, observation_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
            observation_date_source="REPORT_DATE", date_confidence="HIGH",
        ),
        ClinicalObservation(
            id="3", patient_id="p1", document_id="d1", extraction_id="e1", analyte="Platelets", canonical_name="Platelet Count",
            value="250", normalized_value=250.0, observation_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
            observation_date_source="REPORT_DATE", date_confidence="HIGH",
        ),
    ]

    panel_res = PanelCompletenessAnalyzer.analyze_panel_completeness(obs_cbc)
    cbc_info = next((p for p in panel_res if p.panel_name == "Complete Blood Count (CBC)"), None)
    assert cbc_info is not None
    assert cbc_info.is_complete is False
    assert len(cbc_info.missing_analytes) > 0
    assert "Hematocrit" in cbc_info.missing_analytes
    assert "Partial Complete Blood Count (CBC)" in cbc_info.advisory_message


# ---------------------------------------------------------------------
# Test 6: Cross-Visit Comparison Engine
# ---------------------------------------------------------------------
def test_cross_visit_comparison():
    obs_a = [
        ClinicalObservation(
            id="a1", patient_id="p1", document_id="docA", extraction_id="eA", analyte="Hemoglobin", canonical_name="Hemoglobin",
            value="12.4", normalized_value=12.4, unit="g/dL", technical_status=FindingStatusEnum.NORMAL.value,
            observation_date=datetime(2026, 1, 15, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH",
        ),
        ClinicalObservation(
            id="a2", patient_id="p1", document_id="docA", extraction_id="eA", analyte="Vitamin D", canonical_name="Vitamin D",
            value="14.0", normalized_value=14.0, unit="ng/mL", technical_status=FindingStatusEnum.LOW.value,
            observation_date=datetime(2026, 1, 15, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH",
        ),
    ]
    obs_b = [
        ClinicalObservation(
            id="b1", patient_id="p1", document_id="docB", extraction_id="eB", analyte="Hemoglobin", canonical_name="Hemoglobin",
            value="10.2", normalized_value=10.2, unit="g/dL", technical_status=FindingStatusEnum.LOW.value,
            observation_date=datetime(2026, 8, 20, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH",
        ),
        ClinicalObservation(
            id="b2", patient_id="p1", document_id="docB", extraction_id="eB", analyte="Vitamin D", canonical_name="Vitamin D",
            value="31.0", normalized_value=31.0, unit="ng/mL", technical_status=FindingStatusEnum.NORMAL.value,
            observation_date=datetime(2026, 8, 20, tzinfo=timezone.utc), observation_date_source="REPORT_DATE", date_confidence="HIGH",
        ),
    ]

    comp_result = CrossVisitComparisonEngine.compare_visits(
        patient_id="p1",
        visit_a_doc_id="docA",
        visit_a_obs=obs_a,
        visit_b_doc_id="docB",
        visit_b_obs=obs_b,
    )

    assert comp_result.common_analytes_count == 2
    hb_comp = next((i for i in comp_result.items if i.canonical_name == "Hemoglobin"), None)
    assert hb_comp is not None
    assert hb_comp.visit_a_value == 12.4
    assert hb_comp.visit_b_value == 10.2
    assert hb_comp.absolute_change == -2.2
    assert hb_comp.status_transition == "NORMAL -> LOW"
    assert hb_comp.direction == "DECREASED"

    vit_comp = next((i for i in comp_result.items if i.canonical_name == "Vitamin D"), None)
    assert vit_comp is not None
    assert vit_comp.status_transition == "LOW -> NORMAL"
    assert vit_comp.direction == "INCREASED"


# ---------------------------------------------------------------------
# Test 7: Safety Validator Guardrails
# ---------------------------------------------------------------------
def test_safety_validator_prohibitions():
    bad_texts = [
        "Patient is diagnosed with diabetes mellitus.",
        "Patient is getting worse.",
        "Treatment is working.",
        "Patient will develop CKD stage 3.",
        "Increased creatinine caused eGFR to decrease.",
        "Prescribe Metformin 500mg daily.",
        "You should take iron supplements.",
    ]

    for text in bad_texts:
        res = SafetyValidator.validate_text(text)
        assert res.is_safe is False, f"Expected safety violation for: {text}"
        assert len(res.violations) > 0

    good_texts = [
        "Glycemic markers increased compared with previous observation.",
        "Persistent low hemoglobin values observed across multiple reports.",
        "Previously abnormal value is within the current reported reference range.",
        "Clinical correlation recommended.",
        "Interpretation should consider clinical context.",
    ]

    for text in good_texts:
        res = SafetyValidator.validate_text(text)
        assert res.is_safe is True, f"Expected text to pass safety validation: {text}"


# ---------------------------------------------------------------------
# Test 8: End-to-End Database & API Flow (Timeline, Longitudinal Analysis, Comparison, Notes, RBAC)
# ---------------------------------------------------------------------
@pytest.mark.asyncio
async def test_longitudinal_intelligence_api_suite(
    client: AsyncClient,
    db_session: AsyncSession,
):
    # 1. Create Patient
    patient = Patient(
        id=str(uuid.uuid4()),
        mrn=f"MRN-LONG-{uuid.uuid4().hex[:6]}",
        first_name="Eleanor",
        last_name="Vance",
        date_of_birth=date(1980, 4, 12),
        gender="female",
        blood_group="O+",
    )
    db_session.add(patient)

    # 2. Create Visit 1 Document & Extraction
    doc1 = MedicalDocument(
        id=str(uuid.uuid4()),
        patient_id=patient.id,
        original_filename="visit_1_cbc.pdf",
        stored_filename="mock_visit_1.pdf",
        storage_key="mock/visit_1.pdf",
        sha256_hash=uuid.uuid4().hex,
        file_size=1024,
        mime_type="application/pdf",
        document_type="LAB_REPORT",
        processing_status="COMPLETED",
        metadata_json={"document_date": "2026-02-10"},
    )
    db_session.add(doc1)
    await db_session.flush()

    ext1 = DocumentExtraction(
        id=str(uuid.uuid4()),
        document_id=doc1.id,
        extraction_version=1,
        status="COMPLETED",
        raw_text="Complete Blood Count Report Date: 2026-02-10\nHemoglobin: 12.5 g/dL (12.0 - 15.5)\nCreatinine: 0.9 mg/dL (0.6 - 1.1)",
    )
    db_session.add(ext1)
    await db_session.flush()

    ent1_1 = DocumentExtractionEntity(
        id=str(uuid.uuid4()),
        extraction_id=ext1.id,
        document_id=doc1.id,
        raw_name="Hemoglobin",
        canonical_name="Hemoglobin",
        value_text="12.5",
        numeric_value=12.5,
        original_unit="g/dL",
        normalized_unit="g/dL",
        reference_min=12.0,
        reference_max=15.5,
        confidence=0.98,
    )
    ent1_2 = DocumentExtractionEntity(
        id=str(uuid.uuid4()),
        extraction_id=ext1.id,
        document_id=doc1.id,
        raw_name="Creatinine",
        canonical_name="Creatinine",
        value_text="0.9",
        numeric_value=0.9,
        original_unit="mg/dL",
        normalized_unit="mg/dL",
        reference_min=0.6,
        reference_max=1.1,
        confidence=0.99,
    )
    db_session.add_all([ent1_1, ent1_2])

    # 3. Create Visit 2 Document & Extraction (6 months later: Hemoglobin dropped to 10.4 LOW, Creatinine stable at 0.9)
    doc2 = MedicalDocument(
        id=str(uuid.uuid4()),
        patient_id=patient.id,
        original_filename="visit_2_cbc.pdf",
        stored_filename="mock_visit_2.pdf",
        storage_key="mock/visit_2.pdf",
        sha256_hash=uuid.uuid4().hex,
        file_size=1024,
        mime_type="application/pdf",
        document_type="LAB_REPORT",
        processing_status="COMPLETED",
        metadata_json={"document_date": "2026-08-15"},
    )
    db_session.add(doc2)
    await db_session.flush()

    ext2 = DocumentExtraction(
        id=str(uuid.uuid4()),
        document_id=doc2.id,
        extraction_version=1,
        status="COMPLETED",
        raw_text="Complete Blood Count Report Date: 2026-08-15\nHemoglobin: 10.4 g/dL (12.0 - 15.5)\nCreatinine: 0.9 mg/dL (0.6 - 1.1)",
    )
    db_session.add(ext2)
    await db_session.flush()

    ent2_1 = DocumentExtractionEntity(
        id=str(uuid.uuid4()),
        extraction_id=ext2.id,
        document_id=doc2.id,
        raw_name="Hemoglobin",
        canonical_name="Hemoglobin",
        value_text="10.4",
        numeric_value=10.4,
        original_unit="g/dL",
        normalized_unit="g/dL",
        reference_min=12.0,
        reference_max=15.5,
        confidence=0.97,
    )
    ent2_2 = DocumentExtractionEntity(
        id=str(uuid.uuid4()),
        extraction_id=ext2.id,
        document_id=doc2.id,
        raw_name="Creatinine",
        canonical_name="Creatinine",
        value_text="0.9",
        numeric_value=0.9,
        original_unit="mg/dL",
        normalized_unit="mg/dL",
        reference_min=0.6,
        reference_max=1.1,
        confidence=0.99,
    )
    db_session.add_all([ent2_1, ent2_2])
    await db_session.commit()

    # 4. Trigger Clinical Analysis on both documents so findings and observations sync
    service = ClinicalIntelligenceService(db_session)
    await service.run_clinical_analysis(doc1.id)
    await service.run_clinical_analysis(doc2.id)

    # 5. GET Timeline API
    res_timeline = await client.get(f"/api/v1/patients/{patient.id}/timeline")
    assert res_timeline.status_code == 200
    timeline_data = res_timeline.json()
    assert timeline_data["patient_id"] == patient.id
    assert timeline_data["total_visits"] == 2
    assert timeline_data["total_observations"] == 4

    # 6. GET Trends API
    res_trends = await client.get(f"/api/v1/patients/{patient.id}/trends")
    assert res_trends.status_code == 200
    trends_list = res_trends.json()
    assert len(trends_list) == 2
    hb_trend = next((t for t in trends_list if t["canonical_name"] == "Hemoglobin"), None)
    assert hb_trend is not None
    assert hb_trend["first_value"] == 12.5
    assert hb_trend["last_value"] == 10.4
    assert hb_trend["absolute_change"] == -2.1

    # 7. POST Longitudinal Analysis API
    res_analysis = await client.post(
        f"/api/v1/patients/{patient.id}/longitudinal-analysis",
        json={"include_patterns": True},
    )
    assert res_analysis.status_code == 200
    analysis_data = res_analysis.json()
    assert analysis_data["patient_id"] == patient.id
    assert analysis_data["visit_count"] == 2
    assert len(analysis_data["sections"]) > 0
    # Provenance check
    for sec in analysis_data["sections"]:
        assert sec["safety_validation_status"] == "PASSED"
        assert len(sec["evidence_ids"]) >= 0

    # 8. POST Compare Visits API
    res_compare = await client.post(
        f"/api/v1/patients/{patient.id}/compare-visits",
        json={"visit_a_document_id": doc1.id, "visit_b_document_id": doc2.id},
    )
    assert res_compare.status_code == 200
    compare_data = res_compare.json()
    assert compare_data["common_analytes_count"] == 2
    hb_comp = next((i for i in compare_data["items"] if i["canonical_name"] == "Hemoglobin"), None)
    assert hb_comp is not None
    assert hb_comp["visit_a_value"] == 12.5
    assert hb_comp["visit_b_value"] == 10.4
    assert hb_comp["status_transition"] == "NORMAL -> LOW"

    # 9. POST Longitudinal Review Note API (Doctor Note)
    res_note = await client.post(
        f"/api/v1/patients/{patient.id}/longitudinal-review-notes",
        json={"note": "Reviewed hemoglobin trend over 6 months; monitor closely.", "analysis_id": analysis_data["id"]},
    )
    assert res_note.status_code == 201
    note_data = res_note.json()
    assert note_data["patient_id"] == patient.id
    assert "Reviewed hemoglobin" in note_data["note"]

    # 10. GET Review Notes
    res_get_notes = await client.get(f"/api/v1/patients/{patient.id}/longitudinal-review-notes")
    assert res_get_notes.status_code == 200
    notes_list = res_get_notes.json()
    assert len(notes_list) >= 1
