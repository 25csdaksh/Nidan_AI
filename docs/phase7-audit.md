# Phase 7 Audit: Medical Imaging Intelligence (Chest X-Ray Analysis Foundation)

## 1. Executive Summary & Current Architecture Audit

NIDAN AI is an assistive Clinical Decision Support System (CDSS) built across Phases 0–6.
- **Phase 0–1**: Modular FastAPI backend, Next.js 14 frontend, local/S3 storage abstraction (`BaseStorageService`), async queue broker (`BaseTaskBroker`), HIPAA audit logging (`AuditLog`), RBAC, and secure document ingestion (`MedicalDocument`).
- **Phase 2**: Multi-engine OCR & tabular entity extraction (`DocumentExtraction`, `DocumentExtractionEntity`).
- **Phase 3**: Canonical analyte normalization, dynamic reference ranges, and deterministic clinical anomaly engine (`Finding`, `FindingSeverityEnum`).
- **Phase 4**: Longitudinal multi-encounter timeline, trajectory forecasting, velocity calculation, and clinical encounter linking (`LongitudinalObservation`, `EncounterRecord`).
- **Phase 5**: Prescription intelligence, drug interaction rules, dosage verification, allergy cross-matching (`Prescription`, `MedicationItem`, `MedicationSafetyFinding`).
- **Phase 6**: Evidence-grounded Doctor AI Copilot, verifiable provenance retrieval (`EvidenceRetriever`, `EvidenceItem`), strict CDSS hallucination guards (`HallucinationGuard`, `UnsupportedClaimDetector`, `CopilotSafetyValidator`).

Phase 7 introduces **Medical Imaging Intelligence** focusing on Chest X-Ray Analysis Foundation, maintaining strict CDSS safety, verifiable evidence provenance, deterministic preprocessing, model abstraction, and human-in-the-loop clinician review.

---

## 2. Reusable Modules & Infrastructure

| Subsystem | Existing Abstraction | Phase 7 Reuse Strategy |
| :--- | :--- | :--- |
| **Storage** | `BaseStorageService` (`app/core/storage.py`) | Store original DICOM/PNG/JPEG and preprocessed artifacts using hashed key paths (`imaging/{patient_id}/{hash}.{ext}`). |
| **Async Tasks** | `BaseTaskBroker` (`app/core/queue.py`) | Queue image preprocessing, quality gating, model inference, and finding generation via background worker. |
| **Audit Trail** | `AuditLog` (`app/modules/audit/`) | Record `IMAGING_UPLOADED`, `IMAGING_VALIDATED`, `IMAGING_REJECTED`, `IMAGING_ANALYSIS_STARTED`, `IMAGING_ANALYSIS_COMPLETED`, `IMAGING_ANALYSIS_FAILED`, `IMAGING_FINDING_VIEWED`, `IMAGING_FINDING_REVIEWED`, `IMAGING_FINDING_ACCEPTED`, `IMAGING_FINDING_MODIFIED`, `IMAGING_FINDING_REJECTED`, `EXPLAINABILITY_VIEWED`. |
| **Auth & RBAC** | `get_current_user_token`, `RoleEnum` | Restrict clinician reviews to authorized clinical roles (`DOCTOR`, `RADIOLOGIST`, `ADMIN`), enforce strict tenant patient isolation. |
| **Patient Domain** | `Patient` (`app/modules/patients/`) | Link `ImagingStudy` to `patients.id` with cascade deletion and isolation checks. |
| **Medical Documents**| `MedicalDocument` (`app/modules/medical_documents/`) | Optional linkage between uploaded document record and `ImagingStudy`. |
| **Evidence Provenance**| `EvidenceRetriever`, `EvidenceItem` (`app/modules/doctor_copilot/`) | Integrate `EVID-XRAY-{id}` into the centralized evidence catalog and Copilot context. |
| **Safety Validators**| `CopilotSafetyValidator`, `HallucinationGuard` | Extend prohibition checks to reject autonomous imaging diagnoses (e.g. "patient has pneumonia") while supporting probabilistic CDSS claims with `EVID-XRAY` citations. |

---

## 3. Database Changes (Migration `0006_medical_imaging`)

New normalized database tables to create:
1. `imaging_studies`:
   - `id` (UUID PK), `patient_id` (FK patients.id, indexed), `medical_document_id` (FK medical_documents.id nullable), `modality` (Enum: XRAY, CT, MRI, ULTRASOUND), `body_part` (String), `view_position` (PA, AP, Lateral), `study_date` (DateTime), `acquisition_date` (DateTime nullable), `image_count` (Integer), `image_quality_status` (Enum: QUALITY_ACCEPTED, QUALITY_WARNING, QUALITY_REJECTED), `processing_status` (Enum: QUEUED, VALIDATING, PREPROCESSING, RUNNING, COMPLETED, FAILED, REJECTED), `current_analysis_id` (String nullable), `metadata_json` (JSON), `created_at`, `updated_at`.
2. `imaging_images`:
   - `id` (UUID PK), `imaging_study_id` (FK imaging_studies.id, indexed), `storage_key` (String 512, hidden from public APIs), `original_filename` (String), `mime_type` (String), `file_size` (BigInteger), `sha256_hash` (String 64, indexed), `width` (Integer), `height` (Integer), `bit_depth` (Integer), `color_space` (String), `orientation` (String), `metadata_json` (JSON), `created_at`.
3. `imaging_analyses`:
   - `id` (UUID PK), `imaging_study_id` (FK imaging_studies.id, indexed), `model_id` (String), `model_version` (String), `preprocessing_version` (String), `inference_version` (String), `threshold_version` (String), `status` (Enum), `image_quality_status` (Enum), `input_hash` (String 64), `output_json` (JSON), `processing_time_ms` (Integer), `error` (Text nullable), `created_at`, `completed_at`.
4. `imaging_findings`:
   - `id` (UUID PK), `imaging_analysis_id` (FK imaging_analyses.id, indexed), `finding_code` (String, indexed), `finding_name` (String), `anatomical_region` (String), `probability` (Float), `confidence` (Float), `severity` (String), `model_threshold` (Float), `localization_json` (JSON), `explanation` (Text), `evidence_json` (JSON), `review_status` (Enum: PENDING, ACCEPTED, MODIFIED, REJECTED, indexed), `reviewed_by` (FK users.id nullable), `reviewed_at` (DateTime nullable), `clinician_comment` (Text nullable), `created_at`.

---

## 4. API Endpoints to Implement

- `POST /api/v1/patients/{patient_id}/imaging/studies` (Upload & register new imaging study)
- `GET /api/v1/patients/{patient_id}/imaging/studies` (List patient imaging studies)
- `GET /api/v1/imaging/studies/{study_id}` (Get study detail)
- `POST /api/v1/imaging/studies/{study_id}/analyze` (Trigger inference pipeline)
- `GET /api/v1/imaging/analyses/{analysis_id}` (Get analysis status and execution details)
- `GET /api/v1/imaging/analyses/{analysis_id}/findings` (Get structured findings)
- `GET /api/v1/imaging/analyses/{analysis_id}/evidence` (Get evidence provenance for analysis)
- `POST /api/v1/imaging/findings/{finding_id}/review` (Clinician review: ACCEPT, MODIFY, REJECT)
- `GET /api/v1/imaging/analyses/{analysis_id}/explainability` (Get explainability localization & heatmap metadata)
- `GET /api/v1/patients/{patient_id}/imaging/timeline` (Longitudinal imaging timeline)
- `GET /api/v1/imaging/models` (Query approved vision model registry metadata)
- `GET /api/v1/imaging/images/{image_id}/file` (Secure authenticated image proxy)

---

## 5. ML Architecture & Vision Foundation

1. **Model Abstraction (`BaseImagingModel`)**:
   - Standard interface: `load()`, `predict()`, `validate_output()`, `metadata()`.
2. **Model Registry (`ModelRegistry`)**:
   - Controls active vision models (e.g. `XRAY_MODEL_CHEST_V1`).
   - Supports ONNX, TorchScript, PyTorch and deterministic test harness (`TEST_ONLY` mock path for environments without CUDA/Torch weights).
   - Immutable version tracking (`model_id`, `version`, `preprocessing_version`, `threshold_version`, `calibration_version`).
3. **Controlled Label Taxonomy (`xray_label_registry.py`)**:
   - Standard 12+ chest X-ray findings: Cardiomegaly, Pleural Effusion, Atelectasis, Consolidation, Edema, Pneumothorax, Infiltration, Mass, Nodule, Pneumonia, Fibrosis, Pleural Thickening.
   - Non-diagnostic assistive safety language & CDSS guidance per label.
4. **Deterministic Preprocessing (`xray-preprocess-v1`)**:
   - Grayscale conversion, adaptive histogram equalization / CLAHE, aspect-ratio preserving resize (e.g. 224x224 or 512x512), standard tensor normalization ((img - mean)/std).
5. **Image Quality Control Gate**:
   - Evaluates SNR, contrast variance, extreme saturation, blur (Laplacian variance), dimension limits.
   - Quality statuses: `QUALITY_ACCEPTED`, `QUALITY_WARNING`, `QUALITY_REJECTED`.
6. **Explainability Abstraction**:
   - Grad-CAM / Attention heatmap generation metadata and bounded coordinate localization boxes.

---

## 6. Doctor AI Copilot Integration & Safety Boundary

1. **New Context Builder**: `backend/app/modules/doctor_copilot/context/imaging_context.py`
2. **Evidence ID Format**: `EVID-XRAY-{finding_id}`
3. **Safety Guard Enforcements**:
   - Block statements asserting absolute diagnosis (e.g. "Patient has pneumonia").
   - Enforce probabilistic phrasing ("Model detected a pattern associated with...", "Finding requires clinician verification").
   - Mandatory CDSS disclaimers on every imaging endpoint and Copilot response.
4. **Immutability Guarantee**:
   - Clinician review records updates in `ImagingFinding.review_status` and `clinician_comment` without altering original model output (`probability`, `confidence`, `localization_json`).

---

## 7. Frontend Imaging Workspace

- Route: `/patients/[id]/imaging`
- Components:
  - `XRayUploadPanel.tsx` (Drag-and-drop DICOM/PNG/JPEG with client validation)
  - `ImagingStudyCard.tsx` (Study summary & status)
  - `XRayViewer.tsx` (Zoom, pan, contrast/brightness adjustments, reset, fullscreen)
  - `ImagingAnalysisPanel.tsx` (Analysis progress, model version, execution time)
  - `ImagingFindingCard.tsx` (Probability, threshold, confidence, safety disclaimer)
  - `ImagingProbabilityBadge.tsx` (Accessible non-diagnostic probability badges)
  - `ImagingExplainabilityViewer.tsx` (Heatmap/attention overlay viewer)
  - `ImagingEvidenceDrawer.tsx` (Provenance & DICOM metadata inspection)
  - `ImagingReviewModal.tsx` (Accept / Modify / Reject with clinical comments)
  - `ImagingTimeline.tsx` (Longitudinal comparative trajectory across dates)
  - `ImagingSafetyBanner.tsx` (Prominent CDSS assistive banner)

---

## 8. Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| Untrusted file uploads / Path traversal | SHA-256 verification, magic bytes check, file extension whitelist, Pillow integrity decompression, isolated storage paths. |
| Hallucination / Over-reliance on ML | Assistive-only disclaimers, explicit thresholds, mandatory human clinician review, blocked prescriptive text. |
| Model drift / Unreproducible inferences | Strict model, preprocessing, and threshold versioning recorded on every `ImagingAnalysis` record. |
| PHI leakage via DICOM metadata | DICOM anonymization & privacy filter extracting only essential acquisition tags (`StudyInstanceUID`, `Modality`, `ViewPosition`). |
