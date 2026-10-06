# Medical Imaging Intelligence REST API Reference

Base Path: `/api/v1`

---

## 1. Studies & Ingestion

### `POST /api/v1/patients/{patient_id}/imaging/studies`
- **Summary**: Upload and register a new chest X-Ray / DICOM imaging study.
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `file`: Image or DICOM binary (PNG, JPEG, DCM)
  - `modality`: `XRAY` (Default)
  - `body_part`: `CHEST`
  - `view_position`: `PA`, `AP`, `LATERAL`
- **Response**: `201 Created` (`ImagingStudyResponse`)

### `GET /api/v1/patients/{patient_id}/imaging/studies`
- **Summary**: List all imaging studies for a patient ordered by date descending.
- **Response**: `200 OK` (`List[ImagingStudyResponse]`)

### `GET /api/v1/imaging/studies/{study_id}`
- **Summary**: Get detailed study record including images, analysis runs, and active findings.
- **Response**: `200 OK` (`ImagingStudyDetailResponse`)

---

## 2. Inference & Findings

### `POST /api/v1/imaging/studies/{study_id}/analyze`
- **Summary**: Execute or re-run the deterministic preprocessing and vision model pipeline.
- **Response**: `200 OK` (`ImagingAnalysisResponse`)

### `GET /api/v1/imaging/analyses/{analysis_id}`
- **Summary**: Retrieve analysis execution status, metadata, calibration version, and latency.
- **Response**: `200 OK` (`ImagingAnalysisResponse`)

### `GET /api/v1/imaging/analyses/{analysis_id}/findings`
- **Summary**: Retrieve structured findings evaluated for the analysis.
- **Response**: `200 OK` (`List[ImagingFindingResponse]`)

### `GET /api/v1/imaging/analyses/{analysis_id}/evidence`
- **Summary**: Retrieve verifiable `EVID-XRAY-...` provenance objects.
- **Response**: `200 OK` (`List[EvidenceItem]`)

---

## 3. Explainability & Clinician Review

### `GET /api/v1/imaging/analyses/{analysis_id}/explainability?target_label={label}`
- **Summary**: Retrieve attention heatmap (12x12 grid) and localization bounding boxes.
- **Response**: `200 OK` (`ImagingExplainabilityResponse`)

### `POST /api/v1/imaging/findings/{finding_id}/review`
- **Summary**: Clinician review action (Role: `DOCTOR`, `CLINICIAN`, `PHYSICIAN`).
- **Body**:
  ```json
  {
    "review_status": "ACCEPTED",
    "clinician_comment": "Verified right costophrenic angle blunting.",
    "modified_severity": "MODERATE"
  }
  ```
- **Response**: `200 OK` (`ImagingFindingResponse`)

---

## 4. Timeline & Registry

### `GET /api/v1/patients/{patient_id}/imaging/timeline`
- **Summary**: Longitudinal trajectory across all historical chest X-Ray studies.
- **Response**: `200 OK` (`ImagingTimelineResponse`)

### `GET /api/v1/imaging/models`
- **Summary**: List approved vision models from the model registry.
- **Response**: `200 OK` (`List[ImagingModelMetadataResponse]`)

### `GET /api/v1/imaging/images/{image_id}/file`
- **Summary**: Secure authenticated image file stream.
- **Response**: Binary image data (`image/png`, `image/jpeg`).
