# NIDAN AI — Clinical Intelligence & Anomaly Engine (Phase 3)

## 1. Executive Summary

Phase 3 introduces the **Clinical Anomaly Detection & Blood Report Intelligence Engine** to the NIDAN AI Clinical Decision Support System (CDSS). 

The engine operates strictly on verified, extracted laboratory entities (Phase 2), applying a deterministic, versioned, and auditable pipeline that evaluates clinical abnormalities, alerts on critical physiological limits, identifies single-analyte deficiencies, infers multi-marker patterns, links traceable evidence, and enforces strict non-diagnostic CDSS safety guardrails.

```
Verified Extracted Lab Data (Phase 2)
              ↓
Reference Range Knowledge Engine (Priority-Governed)
              ↓
Unit-Aware Validation & Standardization
              ↓
Abnormality Classification (NORMAL, LOW, HIGH)
              ↓
Critical Limit Alert Subsystem (CRITICAL_LOW, CRITICAL_HIGH)
              ↓
Controlled Deficiency Marker Detection
              ↓
Deterministic Multi-Marker Pattern Engine
              ↓
Traceable Provenance & Evidence Aggregation
              ↓
Finding Confidence Scoring
              ↓
Safety Guardrail Validator (CDSS Level 1 & 2)
              ↓
Clinician Review & Adjudication Workbench
              ↓
Longitudinal Patient Trajectory Timeline
```

---

## 2. Safety & CDSS Level 1/2 Guardrails

NIDAN AI is a Clinical Decision Support System and is **not an autonomous diagnostic system, prescription engine, or treatment advisor**.

### Permitted Advisory Phrasing
- "Above the applicable reference range"
- "Below the applicable reference range"
- "Critical threshold exceeded according to configured laboratory rule"
- "Finding may be associated with..."
- "Pattern may be consistent with..."
- "Clinical correlation recommended"
- "Requires clinician review"

### Strictly Forbidden Autonomous Claims (Enforced by `SafetyValidator`)
- Definitive diagnosis (e.g. "Diagnosis: Diabetes", "You have anemia")
- Medication prescription or dosage recommendations (e.g. "Take iron 65mg", "Prescribe Metformin")
- Speculative disease labeling without clinician confirmation.

---

## 3. Reference Range Knowledge Engine & Priority Policy

Medical reference intervals vary by age, sex, pregnancy status, and reporting laboratory. The engine evaluates entities following a strict **priority-governed resolution policy**:

1. **Doctor-Reviewed / Laboratory-Validated Range**: Clinician-verified reference bounds from the report.
2. **Report-Provided Reference Range**: Reference intervals extracted directly from document text.
3. **Applicable Configured Knowledge Base**: Partitioned catalog (`CLSI`, `WHO`, `ADA`, `KDIGO`, `AASLD`, `NCEP ATP III`, `ATA`, `Endocrine Society`) matched against patient age, sex, and normalized unit.
4. **UNKNOWN / REFERENCE_RANGE_UNRESOLVED**: If demographics or units are missing, the engine emits a data quality advisory and marks the finding `REVIEW_REQUIRED`.

---

## 4. Deterministic Clinical Rule Framework

All rules derive from `BaseClinicalRule` and specify:
- `rule_id`: Immutable identifier (e.g. `LAB_ABNORMALITY_001`, `CRITICAL_VALUE_001`, `IRON_PATTERN_001`).
- `rule_version`: Version string (e.g. `1.0.0`).
- `applicable_analytes`: Target analytes or wildcards.
- `severity`: `INFO`, `LOW`, `MODERATE`, `HIGH`, `CRITICAL`.
- `source` & `source_version`: Medical standard attribution.

### Supported Multi-Marker Patterns (Version 1.0)
1. **Possible Iron-Deficiency Pattern (`IRON_PATTERN_001`)**:
   - Concordant markers: Low Hemoglobin, Low MCV, Low MCH, Low Ferritin, Low Serum Iron, Elevated TIBC. Requires $\ge 2$ supporting markers.
   - Text: *"Pattern may be consistent with iron deficiency; clinical correlation recommended."*
2. **Possible Macrocytic Pattern (`MACROCYTIC_PATTERN_001`)**:
   - Concordant markers: Elevated MCV, Low Vitamin B12, Low Folic Acid. Requires $\ge 2$ supporting markers.
   - Text: *"Macrocytic pattern observed in the available laboratory data; clinical correlation recommended."*
3. **Possible Glycemic Abnormality Pattern (`GLYCEMIC_PATTERN_001`)**:
   - Concordant markers: Elevated Fasting Glucose ($\ge 126\text{ mg/dL}$), Elevated HbA1c ($\ge 6.5\%$).
   - Text: *"Elevated glycemic markers observed; clinical correlation recommended."*
4. **Possible Renal-Function Abnormality Pattern (`RENAL_PATTERN_001`)**:
   - Concordant markers: Elevated Serum Creatinine, Reduced eGFR, Elevated BUN. Requires $\ge 2$ supporting markers.
   - Text: *"Renal-function-related laboratory abnormalities are present; clinical correlation recommended."*
5. **Possible Hepatic Pattern (`HEPATIC_PATTERN_001`)**:
   - Concordant markers: Elevated ALT, Elevated AST, Elevated Total Bilirubin, Elevated Alkaline Phosphatase. Requires $\ge 2$ supporting markers.
   - Text: *"Hepatic enzyme and marker abnormalities observed; clinical correlation recommended."*

---

## 5. Traceable Provenance & Evidence

Every clinical finding includes an immutable `evidence` array referencing source entities:
```json
{
  "evidence": [
    {
      "entity_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "analyte": "Hemoglobin",
      "value": "9.8",
      "numeric_value": 9.8,
      "unit": "g/dL",
      "status": "LOW",
      "page_number": 1,
      "source_text": "Hemoglobin 9.8 g/dL 12.0 - 16.0",
      "confidence": 0.96,
      "review_status": "ACCEPTED"
    }
  ]
}
```

---

## 6. Doctor Review & Adjudication

Clinicians can review automated findings with three immutable actions:
- `ACCEPTED`: Clinician verifies finding validity.
- `MODIFIED`: Clinician adjusts title, explanation, or adds adjudication notes.
- `REJECTED`: Clinician dismisses finding.

All review actions emit `CLINICAL_FINDING_REVIEWED` audit log events with actor ID, timestamp, and previous vs new states.

---

## 7. Longitudinal Patient Trajectory

The engine structures historical observation time series across key analytes (`Hemoglobin`, `Creatinine`, `HbA1c`, `Vitamin D`, `ALT`, `AST`, `TSH`), enabling longitudinal tracking across patient report encounters.
