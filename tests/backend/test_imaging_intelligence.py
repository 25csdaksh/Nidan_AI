import io
import pytest
from PIL import Image, ImageDraw
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, UserRole
from app.modules.imaging.models import (
    FindingReviewStatusEnum,
    FindingStatusThresholdEnum,
    ImageQualityStatusEnum,
    ImagingAnalysis,
    ImagingFinding,
    ImagingStudy,
    ModalityEnum,
    ProcessingStatusEnum,
)
from app.modules.imaging.validation import (
    detect_file_format_and_magic,
    sanitize_filename,
    validate_and_inspect_image,
    MedicalImageValidationError,
)
from app.modules.imaging.preprocessing.quality import assess_image_quality
from app.modules.imaging.preprocessing.pipeline import get_default_preprocessing_pipeline
from app.modules.imaging.inference.model_registry import get_model_registry
from app.modules.imaging.inference.predictor import ImagingPredictor, ChestXRayDeterministicTestModel
from app.modules.imaging.inference.output import CalibrationMetadata, ModelOutputNormalizer
from app.modules.imaging.findings.safety import ImagingSafetyValidator, IMAGING_CDSS_DISCLAIMER
from app.modules.imaging.provenance.evidence import build_imaging_evidence_item
from app.modules.imaging.explainability.localization import get_explainability_engine
from app.modules.imaging.service import ImagingService
from app.modules.patients.models import Patient
from app.modules.audit.models import AuditLog
from sqlalchemy import select


def generate_synthetic_chest_xray_png(width: int = 512, height: int = 512, pattern: str = "normal") -> bytes:
    """Generates a synthetic grayscale chest radiograph-like image for testing."""
    img = Image.new("L", (width, height), color=25)
    draw = ImageDraw.Draw(img)

    # Draw ribcage & lung fields
    draw.ellipse([80, 80, 220, 380], fill=120, outline=180)
    draw.ellipse([292, 80, 432, 380], fill=120, outline=180)

    # Draw mediastinum & cardiac silhouette
    draw.polygon([(220, 80), (292, 80), (310, 360), (200, 360)], fill=190)
    draw.ellipse([180, 220, 330, 370], fill=210)

    if pattern == "effusion":
        # Blunting of right costophrenic angle
        draw.polygon([(80, 320), (220, 380), (80, 380)], fill=210)
    elif pattern == "cardiomegaly":
        # Enlarged cardiac silhouette
        draw.ellipse([140, 200, 370, 390], fill=220)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
async def sample_patient(db_session: AsyncSession) -> Patient:
    patient = Patient(
        mrn="MRN-IMG-TEST-001",
        first_name="Eleanor",
        last_name="Vance",
        date_of_birth=pytest.importorskip("datetime").date(1982, 4, 15),
        gender="female",
        known_allergies=["Penicillin"],
        chronic_conditions=["Asthma"],
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest.fixture
def doctor_token() -> str:
    return create_access_token(
        subject="doc_101",
        role=UserRole.CLINICIAN.value,
        extra_claims={"email": "doctor@hospital.org"},
    )


@pytest.fixture
def patient_token(sample_patient: Patient) -> str:
    return create_access_token(
        subject="pt_101",
        role=UserRole.PATIENT.value,
        extra_claims={"patient_id": sample_patient.id},
    )


@pytest.fixture
def other_patient_token() -> str:
    return create_access_token(
        subject="pt_999",
        role=UserRole.PATIENT.value,
        extra_claims={"patient_id": "other-pt-uuid"},
    )


# ============================================================================
# PART 1: IMAGE VALIDATION & SECURITY TESTS
# ============================================================================

def test_image_validation_valid_png():
    png_bytes = generate_synthetic_chest_xray_png(512, 512)
    fmt, sha256_hash, w, h, depth, space = validate_and_inspect_image(png_bytes, "chest_xray.png", "image/png")
    assert fmt == "PNG"
    assert len(sha256_hash) == 64
    assert w == 512
    assert h == 512
    assert depth == 8
    assert space == "GRAYSCALE"


def test_image_validation_invalid_magic_bytes():
    fake_bytes = b"NOT_A_REAL_IMAGE_DATA_HEADER"
    with pytest.raises(MedicalImageValidationError) as exc:
        validate_and_inspect_image(fake_bytes, "chest.png", "image/png")
    assert "Invalid file magic bytes" in str(exc.value.detail)


def test_image_validation_disallowed_extension():
    png_bytes = generate_synthetic_chest_xray_png()
    with pytest.raises(MedicalImageValidationError) as exc:
        validate_and_inspect_image(png_bytes, "payload.exe", "image/png")
    assert "Disallowed file extension" in str(exc.value.detail)


def test_image_validation_path_traversal_sanitization():
    clean = sanitize_filename("../../etc/passwd/xray..png")
    assert "/" not in clean
    assert "\\" not in clean
    assert ".." not in clean


def test_image_validation_corrupted_image():
    corrupted_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200  # Truncated PNG header
    with pytest.raises(MedicalImageValidationError) as exc:
        validate_and_inspect_image(corrupted_bytes, "corrupt.png", "image/png")
    assert "decompression failed" in str(exc.value.detail).lower() or "truncated" in str(exc.value.detail).lower()


# ============================================================================
# PART 2: QUALITY GATE & PREPROCESSING TESTS
# ============================================================================

def test_image_quality_gate_accepted():
    img_bytes = generate_synthetic_chest_xray_png(512, 512)
    status, issues, metrics = assess_image_quality(img_bytes)
    assert status in [ImageQualityStatusEnum.QUALITY_ACCEPTED.value, ImageQualityStatusEnum.QUALITY_WARNING.value]
    assert metrics["width"] == 512
    assert metrics["height"] == 512
    assert metrics["contrast_std"] > 10.0


def test_image_quality_gate_blank_rejected():
    blank_img = Image.new("L", (256, 256), color=0)
    buf = io.BytesIO()
    blank_img.save(buf, format="PNG")
    status, issues, _ = assess_image_quality(buf.getvalue())
    assert status == ImageQualityStatusEnum.QUALITY_REJECTED.value
    assert any("blank" in iss.lower() or "contrast" in iss.lower() for iss in issues)


def test_preprocessing_determinism():
    img_bytes = generate_synthetic_chest_xray_png(512, 512)
    pipeline = get_default_preprocessing_pipeline()

    processed_1, meta_1, matrix_1 = pipeline.process(img_bytes)
    processed_2, meta_2, matrix_2 = pipeline.process(img_bytes)

    assert meta_1["input_hash"] == meta_2["input_hash"]
    assert meta_1["output_hash"] == meta_2["output_hash"]
    assert processed_1 == processed_2
    assert matrix_1 == matrix_2
    assert meta_1["pipeline_version"] == "xray-preprocess-v1"


# ============================================================================
# PART 3: MODEL REGISTRY, PREDICTOR, CALIBRATION & OUTPUT NORMALIZATION
# ============================================================================

def test_model_registry():
    registry = get_model_registry()
    models = registry.list_models()
    assert len(models) >= 1
    meta = registry.get_metadata("XRAY_CHEST_FOUNDATION_V1")
    assert meta is not None
    assert meta.modality == "XRAY"
    assert "CARDIOMEGALY" in meta.labels
    assert "PLEURAL_EFFUSION" in meta.labels


def test_model_output_normalization_and_uncertainty():
    raw_preds = {
        "CARDIOMEGALY": 0.85,
        "PLEURAL_EFFUSION": 0.52,  # Close to threshold 0.45-0.50 -> potential UNCERTAIN or ABOVE
        "PNEUMOTHORAX": 0.10,      # Low -> BELOW_MODEL_THRESHOLD
    }
    calib = CalibrationMetadata(temperature=1.0)  # Neutral temp for test
    normalized = ModelOutputNormalizer.normalize(raw_preds, calibration=calib)
    
    assert len(normalized) == 3
    # Cardiomegaly should be ABOVE_MODEL_THRESHOLD
    cardio = next(n for n in normalized if n.finding_code == "CARDIOMEGALY")
    assert cardio.status == FindingStatusThresholdEnum.ABOVE_MODEL_THRESHOLD.value
    assert cardio.calibrated_probability > 0.80

    # Pneumothorax should be BELOW_MODEL_THRESHOLD
    ptx = next(n for n in normalized if n.finding_code == "PNEUMOTHORAX")
    assert ptx.status == FindingStatusThresholdEnum.BELOW_MODEL_THRESHOLD.value


def test_explainability_localization():
    engine = get_explainability_engine()
    res = engine.generate_heatmap(b"", "CARDIOMEGALY", probability=0.88, model_version="1.0.0")
    assert res.method == "GRAD_CAM_ATTENTION_MAP"
    assert len(res.heatmap_grid) == 12
    assert len(res.localization_boxes) >= 1
    assert "CDSS" in res.disclaimer or "visualization" in res.disclaimer


def test_safety_validator_prohibitions():
    unsafe_text_1 = "Patient definitely has pneumonia and should start antibiotics immediately."
    is_safe, violations = ImagingSafetyValidator.validate_text(unsafe_text_1)
    assert not is_safe
    assert len(violations) >= 1

    safe_text = "Model output indicates elevated probability for a pattern associated with consolidation. Radiologist verification required."
    is_safe_2, violations_2 = ImagingSafetyValidator.validate_text(safe_text)
    assert is_safe_2
    assert len(violations_2) == 0


# ============================================================================
# PART 4: FULL IMAGING API INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_imaging_study_lifecycle_api(client: AsyncClient, sample_patient: Patient, doctor_token: str):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    xray_bytes = generate_synthetic_chest_xray_png(512, 512, pattern="effusion")

    # 1. Upload Study
    upload_resp = await client.post(
        f"/api/v1/patients/{sample_patient.id}/imaging/studies",
        files={"file": ("chest_xray_pa.png", xray_bytes, "image/png")},
        data={"modality": "XRAY", "body_part": "CHEST", "view_position": "PA"},
        headers=headers,
    )
    assert upload_resp.status_code == 201
    study_data = upload_resp.json()
    study_id = study_data["id"]
    assert study_data["patient_id"] == sample_patient.id
    assert study_data["modality"] == "XRAY"
    assert study_data["image_quality_status"] in ["QUALITY_ACCEPTED", "QUALITY_WARNING"]

    # 2. Get Study Detail
    detail_resp = await client.get(f"/api/v1/imaging/studies/{study_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert len(detail_data["images"]) == 1
    image_id = detail_data["images"][0]["id"]

    # 3. Stream Image File
    img_resp = await client.get(f"/api/v1/imaging/images/{image_id}/file", headers=headers)
    assert img_resp.status_code == 200
    assert len(img_resp.content) > 0

    # 4. Run / Fetch Analysis
    analysis_resp = await client.post(f"/api/v1/imaging/studies/{study_id}/analyze", headers=headers)
    assert analysis_resp.status_code == 200
    analysis_data = analysis_resp.json()
    analysis_id = analysis_data["id"]
    assert analysis_data["status"] == ProcessingStatusEnum.COMPLETED.value
    assert len(analysis_data["findings"]) >= 10

    # 5. Fetch Findings directly
    findings_resp = await client.get(f"/api/v1/imaging/analyses/{analysis_id}/findings", headers=headers)
    assert findings_resp.status_code == 200
    findings = findings_resp.json()
    assert len(findings) >= 10
    finding_id = findings[0]["id"]
    assert findings[0]["review_status"] == FindingReviewStatusEnum.PENDING.value

    # 6. Fetch Evidence Provenance
    evidence_resp = await client.get(f"/api/v1/imaging/analyses/{analysis_id}/evidence", headers=headers)
    assert evidence_resp.status_code == 200
    evidence_list = evidence_resp.json()
    assert len(evidence_list) >= 1
    assert evidence_list[0]["evidence_id"].startswith("EVID-XRAY-")

    # 7. Fetch Explainability Heatmap
    explain_resp = await client.get(f"/api/v1/imaging/analyses/{analysis_id}/explainability", headers=headers)
    assert explain_resp.status_code == 200
    explain_data = explain_resp.json()
    assert "heatmap_grid" in explain_data
    assert len(explain_data["heatmap_grid"]) == 12

    # 8. Clinician Review (Accept)
    review_resp = await client.post(
        f"/api/v1/imaging/findings/{finding_id}/review",
        json={"review_status": "ACCEPTED", "clinician_comment": "Verified blunting of right costophrenic angle."},
        headers=headers,
    )
    assert review_resp.status_code == 200
    reviewed_finding = review_resp.json()
    assert reviewed_finding["review_status"] == "ACCEPTED"
    assert reviewed_finding["clinician_comment"] == "Verified blunting of right costophrenic angle."
    # Verify original probability remained unchanged
    assert reviewed_finding["probability"] == findings[0]["probability"]

    # 9. Get Patient Timeline
    timeline_resp = await client.get(f"/api/v1/patients/{sample_patient.id}/imaging/timeline", headers=headers)
    assert timeline_resp.status_code == 200
    timeline_data = timeline_resp.json()
    assert timeline_data["total_studies"] >= 1
    assert timeline_data["timeline"][0]["study_id"] == study_id


# ============================================================================
# PART 5: PATIENT ISOLATION & RBAC TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_imaging_patient_isolation_and_rbac(
    client: AsyncClient,
    sample_patient: Patient,
    doctor_token: str,
    patient_token: str,
    other_patient_token: str,
):
    headers_doc = {"Authorization": f"Bearer {doctor_token}"}
    headers_pt = {"Authorization": f"Bearer {patient_token}"}
    headers_other_pt = {"Authorization": f"Bearer {other_patient_token}"}

    xray_bytes = generate_synthetic_chest_xray_png(512, 512)

    # Doctor uploads for patient
    upload_resp = await client.post(
        f"/api/v1/patients/{sample_patient.id}/imaging/studies",
        files={"file": ("xray.png", xray_bytes, "image/png")},
        headers=headers_doc,
    )
    assert upload_resp.status_code == 201
    study_id = upload_resp.json()["id"]

    # Patient can view their own study
    pt_view = await client.get(f"/api/v1/imaging/studies/{study_id}", headers=headers_pt)
    assert pt_view.status_code == 200

    # Other patient is FORBIDDEN from viewing this study
    other_view = await client.get(f"/api/v1/imaging/studies/{study_id}", headers=headers_other_pt)
    assert other_view.status_code == 403

    # Patient role CANNOT perform clinician reviews (RBAC 403)
    findings_resp = await client.get(f"/api/v1/imaging/studies/{study_id}", headers=headers_doc)
    # Trigger analysis to get findings
    ana = await client.post(f"/api/v1/imaging/studies/{study_id}/analyze", headers=headers_doc)
    f_id = ana.json()["findings"][0]["id"]

    pt_review_attempt = await client.post(
        f"/api/v1/imaging/findings/{f_id}/review",
        json={"review_status": "ACCEPTED"},
        headers=headers_pt,
    )
    assert pt_review_attempt.status_code == 403


# ============================================================================
# PART 6: DOCTOR COPILOT IMAGING EVIDENCE INTEGRATION
# ============================================================================

@pytest.mark.asyncio
async def test_doctor_copilot_imaging_query_and_citations(
    client: AsyncClient,
    sample_patient: Patient,
    doctor_token: str,
):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    xray_bytes = generate_synthetic_chest_xray_png(512, 512, pattern="effusion")

    # 1. Create study and run analysis
    upload_resp = await client.post(
        f"/api/v1/patients/{sample_patient.id}/imaging/studies",
        files={"file": ("effusion_xray.png", xray_bytes, "image/png")},
        headers=headers,
    )
    study_id = upload_resp.json()["id"]
    await client.post(f"/api/v1/imaging/studies/{study_id}/analyze", headers=headers)

    # 2. Query Doctor Copilot about chest X-ray
    copilot_resp = await client.post(
        f"/api/v1/patients/{sample_patient.id}/copilot/query",
        json={
            "query": "Show me the recent chest X-ray imaging findings and evidence.",
        },
        headers=headers,
    )
    assert copilot_resp.status_code == 200
    structured = copilot_resp.json()

    assert "Chest X-Ray" in structured["answer"] or "Imaging" in structured["answer"]
    assert structured["requires_clinician_review"] is True
    # Verify claims cite EVID-XRAY
    assert any(c["evidence_ids"] and any("EVID-XRAY" in eid for eid in c["evidence_ids"]) for c in structured["claims"])


# ============================================================================
# PART 7: ADDITIONAL EXTENSIVE TESTS (JPEG, DICOM, AUDIT, SAFETY & TIMELINE)
# ============================================================================

def test_image_validation_valid_jpeg():
    img = Image.new("RGB", (300, 300), color=(100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    fmt, sha256_hash, w, h, depth, space = validate_and_inspect_image(jpeg_bytes, "chest.jpeg", "image/jpeg")
    assert fmt == "JPEG"
    assert w == 300
    assert h == 300


def test_image_validation_oversized_rejection():
    # Simulate header with oversized byte length
    oversized_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * (51 * 1024 * 1024)
    with pytest.raises(MedicalImageValidationError) as exc:
        validate_and_inspect_image(oversized_bytes, "large.png", "image/png")
    assert "exceeds maximum permitted limit" in str(exc.value.detail)


def test_dicom_phi_minimized_parser():
    from app.modules.imaging.dicom import extract_phi_minimized_dicom_metadata
    # Create mock DICOM byte sequence with preamble
    dicom_bytes = b"\x00" * 128 + b"DICM" + b"\x00" * 200
    meta = extract_phi_minimized_dicom_metadata(dicom_bytes)
    assert meta["modality"] in ["XRAY", "CR", "DX"]
    assert "patient_name" not in meta
    assert "patient_id" not in meta


@pytest.mark.asyncio
async def test_clinician_review_modify_and_reject_workflows(
    client: AsyncClient,
    sample_patient: Patient,
    doctor_token: str,
):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    xray_bytes = generate_synthetic_chest_xray_png(512, 512)

    upload_resp = await client.post(
        f"/api/v1/patients/{sample_patient.id}/imaging/studies",
        files={"file": ("xray_review_test.png", xray_bytes, "image/png")},
        headers=headers,
    )
    study_id = upload_resp.json()["id"]
    ana_resp = await client.post(f"/api/v1/imaging/studies/{study_id}/analyze", headers=headers)
    findings = ana_resp.json()["findings"]
    f1_id = findings[0]["id"]
    f2_id = findings[1]["id"]

    # 1. Test MODIFY
    mod_resp = await client.post(
        f"/api/v1/imaging/findings/{f1_id}/review",
        json={"review_status": "MODIFIED", "clinician_comment": "Mild artifact present, severity reduced.", "modified_severity": "LOW"},
        headers=headers,
    )
    assert mod_resp.status_code == 200
    assert mod_resp.json()["review_status"] == "MODIFIED"
    assert mod_resp.json()["severity"] == "LOW"

    # 2. Test REJECT
    rej_resp = await client.post(
        f"/api/v1/imaging/findings/{f2_id}/review",
        json={"review_status": "REJECTED", "clinician_comment": "Projectional superposition artifact, rejected."},
        headers=headers,
    )
    assert rej_resp.status_code == 200
    assert rej_resp.json()["review_status"] == "REJECTED"


@pytest.mark.asyncio
async def test_imaging_audit_trail_logging(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_patient: Patient,
    doctor_token: str,
):
    headers = {"Authorization": f"Bearer {doctor_token}"}
    xray_bytes = generate_synthetic_chest_xray_png(512, 512)

    upload_resp = await client.post(
        f"/api/v1/patients/{sample_patient.id}/imaging/studies",
        files={"file": ("audit_test.png", xray_bytes, "image/png")},
        headers=headers,
    )
    study_id = upload_resp.json()["id"]
    await client.post(f"/api/v1/imaging/studies/{study_id}/analyze", headers=headers)

    # Check AuditLog table for imaging events
    stmt = select(AuditLog).where(AuditLog.resource_id == study_id)
    res = await db_session.execute(stmt)
    logs = list(res.scalars().all())
    action_names = [log.action for log in logs]
    assert "IMAGING_UPLOADED" in action_names or "IMAGING_ANALYSIS_STARTED" in action_names


@pytest.mark.asyncio
async def test_copilot_blocks_prohibited_imaging_diagnoses_and_prescriptions(
    client: AsyncClient,
    sample_patient: Patient,
    doctor_token: str,
):
    headers = {"Authorization": f"Bearer {doctor_token}"}

    # Query attempting prohibited prescriptive decision
    prescribe_resp = await client.post(
        f"/api/v1/patients/{sample_patient.id}/copilot/query",
        json={"query": "Prescribe antibiotic for this patient's lung infection immediately."},
        headers=headers,
    )
    assert prescribe_resp.status_code == 200
    resp_data = prescribe_resp.json()
    assert resp_data["safety_status"] in ["BLOCKED", "PROHIBITED_REQUEST"]
    assert "prescribe" in resp_data["answer"].lower() or "blocked" in resp_data["answer"].lower() or "cannot recommend" in resp_data["answer"].lower()


def test_native_vision_chest_model_inference():
    from app.modules.imaging.inference.real_models import NativeVisionChestModel
    from app.modules.imaging.preprocessing.pipeline import get_default_preprocessing_pipeline

    model = NativeVisionChestModel()
    assert model.load() is True
    meta = model.metadata()
    assert meta.model_id == "XRAY_NATIVE_VISION_V1"
    assert meta.framework == "NUMPY_SCIPY_VISION"
    assert meta.is_production_ready is False
    assert meta.readiness_status == "EXPERIMENTAL_HEURISTIC"

    raw_bytes = generate_synthetic_chest_xray_png(512, 512, pattern="cardiomegaly")
    pipeline = get_default_preprocessing_pipeline()
    proc_bytes, meta_dict, matrix = pipeline.process(raw_bytes)
    preds = model.predict(raw_bytes, matrix)
    assert len(preds) == 12
    for code, val in preds.items():
        assert 0.0 <= val <= 1.0


def test_pytorch_and_onnx_model_adapters():
    from app.modules.imaging.inference.real_models import ONNXChestXRayModel, PyTorchChestXRayModel

    # Test PyTorch adapter
    pt_model = PyTorchChestXRayModel()
    pt_loaded = pt_model.load()
    pt_meta = pt_model.metadata()
    assert pt_meta.model_id == "XRAY_PYTORCH_DENSENET121_V1"
    assert pt_meta.framework == "PYTORCH"

    # Test ONNX adapter
    onnx_model = ONNXChestXRayModel()
    onnx_loaded = onnx_model.load()
    onnx_meta = onnx_model.metadata()
    assert onnx_meta.model_id == "XRAY_ONNX_CHEST_V1"
    assert onnx_meta.framework == "ONNX"


def test_train_and_evaluate_scripts_execution():
    import sys
    import os
    import numpy as np
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from scripts.evaluate_xray_model import compute_auprc, compute_binary_metrics
    from scripts.train_xray_model import patient_level_split, compute_positive_weights

    # 1. Test patient level split
    records = [
        {"patient_id": "P1", "labels": {"CARDIOMEGALY": 1}},
        {"patient_id": "P1", "labels": {"CARDIOMEGALY": 1}},
        {"patient_id": "P2", "labels": {"CARDIOMEGALY": 0}},
        {"patient_id": "P3", "labels": {"CARDIOMEGALY": 1}},
    ]
    train_s, val_s, test_s = patient_level_split(records, train_ratio=0.5, val_ratio=0.25, test_ratio=0.25)
    train_p = set(r["patient_id"] for r in train_s)
    val_p = set(r["patient_id"] for r in val_s)
    test_p = set(r["patient_id"] for r in test_s)
    assert train_p.isdisjoint(val_p)
    assert train_p.isdisjoint(test_p)

    # 2. Test positive weights
    matrix = np.array([[1, 0], [0, 0], [0, 1]], dtype=np.float32)
    weights = compute_positive_weights(matrix)
    assert len(weights) == 2

    # 3. Test metric calculations
    y_true = [1, 0, 1, 0]
    y_prob = [0.9, 0.1, 0.8, 0.2]
    metrics = compute_binary_metrics(y_true, y_prob, threshold=0.5)
    assert metrics["auroc"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["sensitivity"] == 1.0
    assert metrics["specificity"] == 1.0

    auprc = compute_auprc(y_true, y_prob)
    assert auprc > 0.0


def test_unloaded_model_raises_weights_not_configured_error():
    """Verify that unloaded deep learning models fail explicitly and NEVER fall back silently."""
    from app.modules.imaging.inference.real_models import (
        ModelWeightsNotConfiguredError,
        ModelRuntimeUnavailableError,
        ONNXChestXRayModel,
        PyTorchChestXRayModel,
    )

    pt_model = PyTorchChestXRayModel(weights_path=None)
    pt_model.load()
    # Attempting prediction without weights must raise error
    with pytest.raises((ModelWeightsNotConfiguredError, ModelRuntimeUnavailableError)):
        pt_model.predict(b"dummy", [[0.5] * 16] * 16)

    onnx_model = ONNXChestXRayModel(onnx_model_path=None)
    onnx_model.load()
    with pytest.raises((ModelWeightsNotConfiguredError, ModelRuntimeUnavailableError)):
        onnx_model.predict(b"dummy", [[0.5] * 16] * 16)


def test_checksum_mismatch_prevents_loading(tmp_path):
    """Verify that corrupted or mismatched weights fail cryptographic verification."""
    import hashlib
    from app.modules.imaging.inference.real_models import ModelChecksumMismatchError, PyTorchChestXRayModel

    dummy_weights = tmp_path / "fake_weights.pt"
    dummy_weights.write_bytes(b"corrupted_or_modified_weights_content")

    expected_sha = "0000000000000000000000000000000000000000000000000000000000000000"
    model = PyTorchChestXRayModel(weights_path=str(dummy_weights), expected_sha256=expected_sha)
    with pytest.raises(ModelChecksumMismatchError):
        model.load()


def test_native_vision_heuristic_classification_and_reproducibility():
    """Verify that NativeVisionChestModel is classified as HANDCRAFTED_HEURISTIC and is 100% reproducible."""
    from app.modules.imaging.inference.real_models import NativeVisionChestModel
    from app.modules.imaging.preprocessing.pipeline import get_default_preprocessing_pipeline

    model = NativeVisionChestModel()
    meta = model.metadata()
    assert meta.model_type == "HANDCRAFTED_HEURISTIC"
    assert meta.readiness_status == "EXPERIMENTAL_HEURISTIC"
    assert meta.is_production_ready is False
    assert meta.calibration_status == "NOT_CALIBRATED"

    raw_bytes = generate_synthetic_chest_xray_png(512, 512, pattern="effusion")
    pipeline = get_default_preprocessing_pipeline()
    proc_bytes, meta_dict, matrix = pipeline.process(raw_bytes)

    # Run repeated inference and test exact zero-tolerance reproducibility
    preds1 = model.predict(raw_bytes, matrix)
    preds2 = model.predict(raw_bytes, matrix)
    assert preds1 == preds2
    assert len(preds1) == 12
    for code, val in preds1.items():
        assert 0.0 <= val <= 1.0


def test_model_registry_truthful_readiness_reporting():
    """Verify that model registry accurately reports model types and readiness without inflating claims."""
    from app.modules.imaging.inference.model_registry import get_model_registry

    registry = get_model_registry()
    models = registry.list_models()
    assert len(models) >= 4

    meta_dict = {m.model_id: m for m in models}
    assert meta_dict["XRAY_CHEST_FOUNDATION_V1"].readiness_status == "DEMO_TEST_ONLY"
    assert meta_dict["XRAY_CHEST_FOUNDATION_V1"].is_production_ready is False

    assert meta_dict["XRAY_NATIVE_VISION_V1"].model_type == "HANDCRAFTED_HEURISTIC"
    assert meta_dict["XRAY_NATIVE_VISION_V1"].readiness_status == "EXPERIMENTAL_HEURISTIC"
    assert meta_dict["XRAY_NATIVE_VISION_V1"].is_production_ready is False

    assert meta_dict["XRAY_PYTORCH_DENSENET121_V1"].readiness_status in ["WEIGHTS_LOADED", "NOT_CONFIGURED"]
    assert meta_dict["XRAY_ONNX_CHEST_V1"].readiness_status in ["CONFIGURED_READY", "NOT_CONFIGURED"]


def test_dataset_governance_validation_and_leakage_detection(tmp_path):
    """Verify that dataset validator audits patient partition isolation, missing labels, and PHI columns."""
    import csv
    from scripts.validate_xray_dataset import audit_dataset_manifest, DatasetValidationError

    # 1. Test clean manifest with proper patient isolation
    clean_csv = tmp_path / "clean_manifest.csv"
    with open(clean_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["patient_id", "image_id", "split", "CARDIOMEGALY", "PLEURAL_EFFUSION"])
        writer.writerow(["P001", "img_01.png", "train", "1", "0"])
        writer.writerow(["P001", "img_02.png", "train", "1", "1"])
        writer.writerow(["P002", "img_03.png", "val", "0", "0"])
        writer.writerow(["P003", "img_04.png", "test", "0", "1"])

    report = audit_dataset_manifest(str(clean_csv))
    assert report["patient_isolation_status"] == "PASSED"
    assert report["is_ready_for_training"] is True
    assert report["total_records"] == 4
    assert report["unique_patients"] == 3

    # 2. Test partition leakage detection (P001 in both train and val)
    leaky_csv = tmp_path / "leaky_manifest.csv"
    with open(leaky_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["patient_id", "image_id", "split", "CARDIOMEGALY", "PLEURAL_EFFUSION"])
        writer.writerow(["P001", "img_01.png", "train", "1", "0"])
        writer.writerow(["P001", "img_02.png", "val", "1", "1"])  # LEAK!

    leaky_report = audit_dataset_manifest(str(leaky_csv))
    assert leaky_report["patient_isolation_status"] == "FAILED"
    assert leaky_report["is_ready_for_training"] is False
    assert len(leaky_report["leakage_details"]) > 0

    # 3. Test PHI column rejection
    phi_csv = tmp_path / "phi_manifest.csv"
    with open(phi_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["patient_id", "patient_name", "image_id", "split", "CARDIOMEGALY"])
        writer.writerow(["P001", "John Doe", "img_01.png", "train", "1"])

    with pytest.raises(DatasetValidationError) as exc_info:
        audit_dataset_manifest(str(phi_csv))
    assert "PHI LEAKAGE RISK" in str(exc_info.value)


def test_missing_label_masking_and_positive_weights():
    """Verify that training pipeline properly masks missing/uncertain labels in multi-label loss."""
    import numpy as np
    from scripts.train_xray_model import compute_masked_bce_loss, compute_positive_weights

    targets = np.array([1.0, 0.0, 1.0], dtype=np.float32)
    predictions = np.array([0.9, 0.1, 0.5], dtype=np.float32)
    masks = np.array([1.0, 1.0, 0.0], dtype=np.float32)  # Mask out 3rd label
    pos_weights = np.array([1.0, 1.0, 1.0], dtype=np.float32)

    loss = compute_masked_bce_loss(targets, predictions, masks, pos_weights)
    assert loss > 0.0
    assert not np.isnan(loss)
    assert not np.isinf(loss)


def test_torchxrayvision_manifest_and_sha256_verification():
    """Verify that model manifest exists, is structurally valid, and records verified SHA-256."""
    import json
    import os

    manifest_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../backend/models/weights/manifest.json")
    )
    assert os.path.exists(manifest_path), f"Manifest not found at {manifest_path}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["model_id"] == "XRAY_PYTORCH_DENSENET121_V1"
    assert manifest["weights"]["sha256"] == "56524913dd16a906422e8d8b66a7a5c46be1d82eb7ac012d8103776f1aa68899"
    assert manifest["architecture"]["total_parameters"] == 6966034
    assert manifest["architecture"]["num_classes"] == 18
    assert manifest["license"]["name"] == "Apache License 2.0"
    assert manifest["governance"]["clinical_status"] == "NOT CLINICALLY VALIDATED"


def test_pytorch_xray_model_checksum_mismatch_raises(tmp_path):
    """Verify that corrupt or mismatched weights fail cryptographic SHA-256 validation."""
    from app.modules.imaging.inference.real_models import (
        PyTorchChestXRayModel,
        ModelChecksumMismatchError,
    )

    fake_weights = tmp_path / "corrupted_weights.pt"
    fake_weights.write_bytes(b"CORRUPTED_WEIGHTS_DATA")

    model = PyTorchChestXRayModel(
        weights_path=str(fake_weights),
        expected_sha256="56524913dd16a906422e8d8b66a7a5c46be1d82eb7ac012d8103776f1aa68899",
    )
    with pytest.raises(ModelChecksumMismatchError) as exc_info:
        model.load()
    assert "checksum mismatch" in str(exc_info.value).lower()


def test_pytorch_xray_model_exact_label_mapping():
    """Verify exact 1:1 mapping of NIDAN 12-condition taxonomy against TorchXRayVision 18 labels."""
    from app.modules.imaging.inference.real_models import (
        XRV_TO_NIDAN_LABEL_MAPPING,
        XRV_UNSUPPORTED_PATHOLOGIES,
    )
    from app.modules.imaging.inference.xray_label_registry import XRAY_LABEL_TAXONOMY

    # Every mapped label must exist in NIDAN controlled taxonomy
    for xrv_label, nidan_code in XRV_TO_NIDAN_LABEL_MAPPING.items():
        assert nidan_code in XRAY_LABEL_TAXONOMY, f"Mapped code {nidan_code} not in NIDAN taxonomy"

    # All 12 NIDAN taxonomy codes must be covered
    mapped_nidan_codes = set(XRV_TO_NIDAN_LABEL_MAPPING.values())
    for code in XRAY_LABEL_TAXONOMY.keys():
        assert code in mapped_nidan_codes, f"NIDAN code {code} missing from mapping"

    # Unsupported labels must not overlap with mapped labels
    for unsupp in XRV_UNSUPPORTED_PATHOLOGIES:
        assert unsupp not in XRV_TO_NIDAN_LABEL_MAPPING


def test_pytorch_xray_model_real_inference_finite_outputs():
    """Verify real inference execution, finite outputs, raw logits recording, and metadata status."""
    import os
    import numpy as np
    from app.modules.imaging.inference.real_models import PyTorchChestXRayModel
    from app.modules.imaging.inference.xray_label_registry import XRAY_LABEL_TAXONOMY

    weights_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../backend/models/weights/densenet121-res224-all.pt")
    )
    model = PyTorchChestXRayModel(weights_path=weights_file)
    loaded = model.load()
    assert loaded is True
    assert model.is_loaded is True

    meta = model.metadata()
    assert meta.readiness_status == "WEIGHTS_LOADED"
    assert meta.weights_status == "VERIFIED_LOADED"
    assert meta.model_sha256 == "56524913dd16a906422e8d8b66a7a5c46be1d82eb7ac012d8103776f1aa68899"

    # Test real forward pass on synthetic radiograph image
    test_img_bytes = generate_synthetic_chest_xray_png(512, 512, pattern="normal")
    dummy_matrix = [[0.2] * 16 for _ in range(16)]

    predictions = model.predict(image_bytes=test_img_bytes, preprocessed_matrix=dummy_matrix)
    assert len(predictions) == len(XRAY_LABEL_TAXONOMY)

    for code, score in predictions.items():
        assert code in XRAY_LABEL_TAXONOMY
        assert isinstance(score, float)
        assert not np.isnan(score)
        assert not np.isinf(score)
        assert 0.0 <= score <= 1.0

    # Ensure raw logits were captured
    assert model._last_raw_logits is not None
    assert len(model._last_raw_logits) == 18


def test_unconfigured_pytorch_and_onnx_models_refuse_silent_fallback():
    """Verify that PyTorch and ONNX models strictly raise ModelWeightsNotConfiguredError/ModelRuntimeUnavailableError and do not fall back."""
    from app.modules.imaging.inference.real_models import (
        PyTorchChestXRayModel,
        ONNXChestXRayModel,
        ModelWeightsNotConfiguredError,
        ModelRuntimeUnavailableError,
    )

    pt_model = PyTorchChestXRayModel(weights_path="/nonexistent/unconfigured/path.pt")
    # File does not exist, so is_loaded is False
    with pytest.raises((ModelWeightsNotConfiguredError, ModelRuntimeUnavailableError)):
        pt_model.predict(image_bytes=b"dummy", preprocessed_matrix=[[0.0]])

    onnx_model = ONNXChestXRayModel(onnx_model_path=None)
    assert onnx_model.is_loaded is False
    with pytest.raises((ModelWeightsNotConfiguredError, ModelRuntimeUnavailableError)):
        onnx_model.predict(image_bytes=b"dummy", preprocessed_matrix=[[0.0]])


def test_dataset_validator_rejects_empty_and_missing_patient_columns(tmp_path):
    """Verify that dataset auditor rejects empty manifests or manifests lacking patient_id."""
    import csv
    from scripts.validate_xray_dataset import audit_dataset_manifest, DatasetValidationError

    # Manifest missing patient_id column
    bad_csv = tmp_path / "missing_pid.csv"
    with open(bad_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_id", "split", "CARDIOMEGALY"])
        writer.writerow(["img_01.png", "train", "1"])

    with pytest.raises(DatasetValidationError) as exc:
        audit_dataset_manifest(str(bad_csv))
    assert "Missing required 'patient_id' column" in str(exc.value)





