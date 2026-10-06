# Medical Imaging Intelligence Security & Privacy Architecture

## 1. Security Core Principles

1. **Patient Isolation & Multi-Tenancy**:
   - Every imaging study, image file, and finding is keyed to a `patient_id`.
   - Patients can only access their own imaging studies.
   - Cross-patient requests trigger immediate `403 Forbidden` exceptions.
2. **Role-Based Access Control (RBAC)**:
   - Clinician review actions (`/api/v1/imaging/findings/{finding_id}/review`) are strictly restricted to clinical staff roles (`DOCTOR`, `CLINICIAN`, `PHYSICIAN`, `SUPER_ADMIN`, `CHIEF_MEDICAL_OFFICER`).
3. **Upload Sanitization & Magic Byte Verification**:
   - Magic bytes are checked against strict signatures:
     - PNG (`\x89PNG\r\n\x1a\n`)
     - JPEG (`\xff\xd8\xff`)
     - DICOM (`DICM` at byte offset 128)
   - Path traversal characters (`..`, `/`, `\`) are strictly sanitized.
   - Decompression bombs and corrupted files are caught before storage.
   - File size is capped at 50 MB.
4. **Secure Image Storage & Proxying**:
   - Storage keys (`imaging/{patient_id}/{sha256}_{filename}`) are never exposed publicly.
   - Images are served via authenticated streaming proxy endpoints (`/api/v1/imaging/images/{image_id}/file`).
5. **HIPAA & 21 CFR Part 11 Audit Trail**:
   - Comprehensive audit logging for all actions:
     - `IMAGING_UPLOADED`
     - `IMAGING_VALIDATED`
     - `IMAGING_REJECTED`
     - `IMAGING_ANALYSIS_STARTED`
     - `IMAGING_ANALYSIS_COMPLETED`
     - `IMAGING_ANALYSIS_FAILED`
     - `IMAGING_FINDING_VIEWED`
     - `IMAGING_FINDING_REVIEWED`
     - `IMAGING_FINDING_ACCEPTED`
     - `IMAGING_FINDING_MODIFIED`
     - `IMAGING_FINDING_REJECTED`
     - `EXPLAINABILITY_VIEWED`
6. **Model Weight Integrity & Safe Loading**:
   - Model weights must match registered `model_sha256` checksums.
   - Arbitrary model file uploads from users are prohibited.
