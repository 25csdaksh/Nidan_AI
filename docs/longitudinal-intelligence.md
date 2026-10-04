# NIDAN AI — Longitudinal Patient Intelligence Engine (Phase 4)
## Intelligent Clinical Insights across Multi-Visit Encounters

---

## 1. Overview & Architectural Goal

Phase 4 transitions **NIDAN AI** from isolated, document-level laboratory analysis into **Patient-Level Longitudinal Clinical Intelligence**. It enables clinicians to assess chronological trajectories, persistent abnormalities, newly emerging findings, resolved marker values, multi-marker panel completeness, and side-by-side cross-visit comparisons across multiple historical encounters.

```text
+---------------------+     +--------------------------+     +-------------------------------+
|  Medical Documents  | --> | Verified Lab Entities    | --> | Clinical Observation Timeline |
+---------------------+     +--------------------------+     +-------------------------------+
                                                                             |
        +--------------------------------------------------------------------+
        |
        v
+-----------------------+     +-----------------------+     +-------------------------+
| Cross-Visit Comparison| --> | Deterministic Trends  | --> | Abnormality Dynamics    |
+-----------------------+     +-----------------------+     +-------------------------+
                                                                             |
        +--------------------------------------------------------------------+
        |
        v
+-----------------------+     +-----------------------+     +-------------------------+
| Multi-Visit Summary   | --> | Safety Guardrails     | --> | Clinician Review Notes  |
+-----------------------+     +-----------------------+     +-------------------------+
```

---

## 2. Safety & CDSS Level 1/2 Boundaries

NIDAN AI operates strictly as a **Clinical Decision Support System (CDSS)**:
- **Zero Autonomous Disease Diagnosis**: Does not diagnose conditions (e.g., states "Persistent low hemoglobin values observed", never "Patient has iron deficiency anemia").
- **Zero Treatment / Prescription Directives**: Never prescribes drugs, dosages, or therapies.
- **Zero Disease Prognosis / Outcome Predictions**: Never claims future patient disease development.
- **Zero Causal Inferences**: Never claims that one laboratory marker shift caused another.
- **Standard Clinical Terminology**: Employs non-causal descriptors such as *"Trend observed"*, *"Value increased compared with previous observation"*, *"Previously abnormal value is within reported reference range"*, and *"Clinical correlation recommended"*.

---

## 3. Normalized Observation Data Model

Longitudinal clinical data is normalized and indexed in the `clinical_observations` table:

```sql
CREATE TABLE clinical_observations (
    id VARCHAR(36) PRIMARY KEY,
    patient_id VARCHAR(36) REFERENCES patients(id) ON DELETE CASCADE,
    document_id VARCHAR(36) REFERENCES medical_documents(id) ON DELETE CASCADE,
    extraction_id VARCHAR(36) REFERENCES document_extractions(id) ON DELETE CASCADE,
    entity_id VARCHAR(36) REFERENCES document_extraction_entities(id) ON DELETE SET NULL,
    analyte VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255) NOT NULL,
    value VARCHAR(100) NOT NULL,
    normalized_value FLOAT,
    unit VARCHAR(50),
    observation_date TIMESTAMPTZ,
    observation_date_source VARCHAR(50) NOT NULL,
    date_confidence VARCHAR(20) NOT NULL,
    document_date TIMESTAMPTZ,
    technical_status VARCHAR(50) NOT NULL,
    reference_min FLOAT,
    reference_max FLOAT,
    reference_source VARCHAR(50) NOT NULL,
    extraction_confidence FLOAT NOT NULL,
    finding_confidence FLOAT NOT NULL,
    source_text TEXT,
    page_number INT NOT NULL,
    is_doctor_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. Observation Date Resolution Priority

Encounter dates are resolved deterministically using a prioritized fallback framework:

1. **REPORT_DATE** (`HIGH` confidence): Explicit laboratory report / result date parsed from document header.
2. **TEST_DATE** (`HIGH` confidence): Explicit sample / specimen collection date parsed from report.
3. **DOCUMENT_DATE** (`MEDIUM` confidence): Document creation metadata date.
4. **UPLOAD_TIMESTAMP** (`LOW` confidence): Technical upload timestamp used strictly as a fallback.
5. **UNKNOWN** (`LOW` confidence): Observation date remains `NULL` when unresolvable.

---

## 5. Deterministic Trend Engine & Noise Filtering

The `TrendEngine` evaluates chronological series ($\ge 2$ observations) and computes:
- **Absolute Delta**: $\Delta = V_{\text{current}} - V_{\text{previous}}$
- **Percentage Change**: $\% \Delta = \left(\frac{V_{\text{current}} - V_{\text{previous}}}{|V_{\text{previous}}|}\right) \times 100$ (with division-by-zero protection returning `None`).
- **Directional Classification**: `INCREASED`, `DECREASED`, `UNCHANGED`, `INSUFFICIENT_DATA`.
- **Noise / Stability Thresholds**: Changes within `neutral_delta_abs` or `neutral_delta_pct` are marked `UNCHANGED` / `STABLE`.
- **Clinical Trend Trajectory**: Direction is interpreted via analyte reference relationships (e.g., for Hemoglobin when low, an increase is `IMPROVING`; for Creatinine when high, an increase is `WORSENING`).

---

## 6. Abnormality Dynamics Engine

The `AbnormalityDynamicsEngine` classifies multi-visit state transitions:
1. **Persistent Abnormality**: Abnormal status across $\ge 2$ consecutive or recent observations (`LOW -> LOW -> LOW`).
2. **New Abnormality**: Transition from normal to abnormal (`NORMAL -> LOW` or `NORMAL -> HIGH`).
3. **Resolved Abnormality**: Transition from abnormal to normal (`LOW -> NORMAL` or `HIGH -> NORMAL`).
4. **Recurring Abnormality**: Abnormal finding reappearing after normalization (`LOW -> NORMAL -> LOW`).
5. **Fluctuating Values**: Multi-visit bidirectional fluctuation (`HIGH -> LOW -> HIGH`).

---

## 7. Panel Completeness & Cross-Visit Comparison

- **Panel Completeness**: Analyzes presence of standard panel markers (`CBC`, `LFT`, `KFT`, `Lipid Profile`, `Thyroid Panel`, `Iron Metabolism`, `Glycemic Panel`). Partial panels are explicitly flagged (e.g., *"Partial CBC data available"*), avoiding false assumptions of normalcy for unmeasured tests.
- **Cross-Visit Comparison Engine**: Directly compares any two encounters (Visit A vs Visit B), computing analyte-by-analyte absolute deltas, percentage shifts, and status transitions.

---

## 8. Multi-Visit Summary & Section Traceability

The `LongitudinalSummaryEngine` synthesizes structured clinical summaries with traceable provenance:
- **Overview**: Encounter period, total reports, observation count.
- **Key Laboratory Trends**: Observable numerical trajectories.
- **Persistent Abnormalities**: Multi-report abnormal persistence.
- **New & Resolved Findings**: Acute shifts and reference interval normalizations.
- **Data Quality & Panel Completeness**: Timestamp sources and incomplete panel warnings.
- **Traceable Provenance**: Each section links to underlying observation IDs and document IDs ("Why did NIDAN AI conclude this?").

---

## 9. Clinician Longitudinal Review Notes & RBAC

- **Authorized Clinicians**: Can create, update, and review timestamped longitudinal clinical review notes (`longitudinal_review_notes`).
- **Patients**: Can view their own longitudinal timeline and summaries, with strict role-based patient isolation preventing modification of clinical findings or creation of clinician notes.
- **Audit Logging**: Sensitive operations record immutable audit events (`LONGITUDINAL_ANALYSIS_STARTED`, `LONGITUDINAL_ANALYSIS_COMPLETED`, `LONGITUDINAL_SUMMARY_VIEWED`, `LONGITUDINAL_COMPARISON_VIEWED`, `LONGITUDINAL_REVIEW_NOTE_CREATED`).

---

## 10. API Endpoints Reference

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/patients/{patient_id}/timeline` | Patient (Self) / Clinical Staff | Chronological encounter observation timeline |
| `GET` | `/api/v1/patients/{patient_id}/trends` | Patient (Self) / Clinical Staff | Multi-analyte calculated trends |
| `GET` | `/api/v1/patients/{patient_id}/trends/{analyte}` | Patient (Self) / Clinical Staff | Specific analyte trend trajectory |
| `POST` | `/api/v1/patients/{patient_id}/longitudinal-analysis` | Patient (Self) / Clinical Staff | Execute multi-visit longitudinal analysis |
| `GET` | `/api/v1/patients/{patient_id}/longitudinal-analysis` | Patient (Self) / Clinical Staff | Retrieve latest longitudinal analysis |
| `GET` | `/api/v1/patients/{patient_id}/longitudinal-analysis/{id}` | Patient (Self) / Clinical Staff | Retrieve specific versioned analysis |
| `POST` | `/api/v1/patients/{patient_id}/compare-visits` | Patient (Self) / Clinical Staff | Direct Visit A vs Visit B comparison |
| `POST` | `/api/v1/patients/{patient_id}/longitudinal-review-notes` | Clinical Staff Only | Create clinician review annotation |
| `GET` | `/api/v1/patients/{patient_id}/longitudinal-review-notes` | Patient (Self) / Clinical Staff | List clinician review annotations |
