# NIDAN AI Security & Compliance Principles

## 1. Compliance Baseline
NIDAN AI is architected with strict adherence to healthcare software standards:
- **HIPAA** (Health Insurance Portability and Accountability Act - Security & Privacy Rules).
- **DISHA** (Digital Information Security in Healthcare Act) / Indian EHR Standards.
- **GDPR / DPDP Act** for strict personal data sovereignty and consent management.

## 2. Protected Health Information (PHI) Handling
1. **Encryption at Rest**:
   - Database tables containing direct identifiers (e.g., patient names, contact info) utilize transparent column-level encryption / AES-256 storage.
   - Object storage artifacts (PDFs, raw lab scans, DICOM images) are encrypted with customer-managed keys (SSE-KMS or AES-256).
2. **Encryption in Transit**:
   - Enforced TLS 1.3 on all external endpoints.
   - mTLS for microservices or worker-to-database connections in production.
3. **De-Identification & Redaction Pipeline**:
   - Before feeding documents into AI/OCR workers, personal identifiers are tagged and separated into secure vaults.

## 3. Mandatory Clinical Decision Support (CDSS) Guardrails
NIDAN AI operates strictly under CDSS Level 1 & 2 guidelines:
- **Human-in-the-Loop (HITL) Enforcement**: AI insights are marked as unverified suggestions until a licensed doctor reviews, confirms, adjusts, or rejects them.
- **Explainability**: Every extracted finding links back to its source document coordinate or laboratory reference interval.
- **Non-Diagnostic Policy**: System prompts and algorithmic models are barred from emitting prescriptive diagnoses or therapeutic regimens without clinician oversight.

## 4. Comprehensive Audit Trails
The `audit` module records all interactions:
- **Actor Identification**: Clinician ID, IP address, device footprint.
- **Action Type**: `VIEW_PATIENT_RECORD`, `EXPORT_REPORT`, `OVERRIDE_LAB_FLAG`, `APPROVE_SUMMARY`.
- **Timestamp & Request ID**: Cryptographically tamper-evident event chains.
- **Immutable Log Store**: Audit tables cannot be updated or deleted by normal application roles.

## 5. Role-Based Access Control (RBAC) & Least Privilege
| Role | View Records | Upload Docs | Verify Insights | System Config | View Audit |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Super Admin | ❌ (No PHI) | ❌ | ❌ | ✅ | ✅ |
| Chief Medical Officer | ✅ | ✅ | ✅ | ✅ | ✅ |
| Physician | ✅ | ✅ | ✅ | ❌ | ❌ |
| Nurse Practitioner | ✅ | ✅ | ❌ | ❌ | ❌ |
| Lab Technician | ✅ (Lab only)| ✅ | ❌ | ❌ | ❌ |
| Compliance Auditor | ❌ (De-id only)| ❌ | ❌ | ❌ | ✅ |
