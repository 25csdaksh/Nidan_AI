# NIDAN AI — Phase 5: Prescription Intelligence & Medication Safety Engine

## 1. Executive Overview
NIDAN AI Phase 5 transforms the platform from multi-visit laboratory analytics into **Prescription-Aware Clinical Decision Support (CDSS Level 1 & 2)**.

The system ingests digital and scanned prescription documents, extracts and normalizes medication entities, and executes deterministic safety screening across:
1. **Drug-Drug Interactions (DDIs)**
2. **Documented Patient Allergy Cross-Referencing**
3. **Duplicate Medication & Generic Overlap Detection**
4. **Lab-Medication Contextual Signals** (e.g. Metformin in renal impairment, ACEi/ARBs in hyperkalemia, Statins in hepatic elevation)
5. **Clinical Contraindications & Chronic Disease Screening**
6. **Longitudinal Medication History & Regimen Timelines**
7. **Clinician Review & Verification Workflows** with HIPAA-compliant audit logging.

> ⚠️ **MANDATORY CLINICAL SAFETY NOTICE**:  
> **NIDAN AI is NOT an autonomous prescribing engine or doctor replacement.** It strictly adheres to CDSS Level 1 & 2 guidelines. It never diagnoses conditions, prescribes drugs, adjusts dosages, claims prognosis, or asserts causal relationships. All safety findings require licensed clinician verification.

---

## 2. Architecture & Data Flow

```text
Prescription Medical Document (PDF / Image)
            ↓
OCR & Text Extraction Pipeline (Phase 2)
            ↓
PrescriptionExtractor & MedicationParser
  ├─ Normalization Engine (Canonical & Generic Names)
  ├─ Dosage, Form & Strength Parser
  ├─ Route Parser (Strict Non-Inference Policy)
  ├─ Frequency & PRN Parser
  └─ Duration Parser (Quantity vs Duration Separation)
            ↓
Database Persistence (prescriptions & prescription_medications)
            ↓
Multi-Engine Medication Safety Pipeline
  ├─ InteractionEngine (Rule-backed DDIs)
  ├─ DuplicateEngine (Exact & Class overlaps)
  ├─ AllergyEngine (Patient allergy cross-referencing)
  ├─ LabContextEngine (Correlated with Phase 3/4 Observations)
  └─ ContraindicationEngine (Patient chronic conditions)
            ↓
MedicationSafetyValidator (CDSS Guardrail Filter)
            ↓
medication_safety_findings (Structured Auditable Alerts)
            ↓
Clinician Review & Interactive Patient Timeline
```

---

## 3. Core Modules & Engine Specifications

### 3.1 Medication Normalization & Non-Hallucination Policy
- **Vocabulary Catalog** (`vocabulary.py`): Controlled catalog of standard generic and brand names, dosage forms, routes, and frequency codes.
- **Normalization Engine** (`normalization.py`): Strips leading numbers, bullet points, and dosage forms (`Tab`, `Cap`, `Inj`, `Syp`) to match canonical names.
- **Strict Non-Hallucination Policy**: If a medication name is unconfirmed or ambiguous, it resolves to `UNKNOWN` with confidence capped at `<= 0.45` to enforce mandatory clinician review.

### 3.2 Parsing Sub-Engines
1. **Dosage & Strength Parser** (`dosage_parser.py`):
   - Extracts numeric values and standard units (`mg`, `mcg`, `g`, `ml`, `IU`, `%`, `meq`).
   - Parses explicit dose quantities (e.g., `1 tablet`, `2 puffs`, `5 ml`).
2. **Route Parser** (`route_parser.py`):
   - Extracts explicit routes (`ORAL`, `INTRAVENOUS`, `INTRAMUSCULAR`, `SUBCUTANEOUS`, `TOPICAL`, `OPHTHALMIC`, `INHALED`, etc.).
   - *Strict Rule*: Refuses to infer route from dosage form alone (e.g. tablet is not assumed oral unless explicitly stated or validated).
3. **Frequency Parser** (`frequency_parser.py`):
   - Prioritizes explicit daily frequencies (`OD`, `BID`, `TID`, `QID`, `Q8H`, `Q12H`, `1-0-1`, `PRN`, `SOS`).
4. **Duration Parser** (`duration_parser.py`):
   - Extracts explicit durations (e.g., `5 days`, `2 weeks`, `1 month`).
   - *Quantity Distinction*: Refuses to convert quantity into duration (e.g., `10 tablets` is NOT `10 days`).

---

## 4. Multi-Engine Safety Architecture

### 4.1 Drug-Drug Interaction (DDI) Engine (`interaction_engine.py`)
- Evaluates co-prescribed and active patient medications against curated, versioned interaction rules.
- *Strict Rule*: An LLM is never the authoritative interaction database. Only validated, evidence-backed rules are evaluated.
- Rule examples:
  - `DDI-WAR-ASP-001`: Warfarin + Aspirin (Increased bleeding risk)
  - `DDI-SPRO-ACEI-003`: Spironolactone + Ramipril (Hyperkalemia risk)
  - `DDI-DIG-AMIO-010`: Digoxin + Amiodarone (Digoxin toxicity risk)
  - `DDI-CLOP-OMEP-002`: Clopidogrel + Omeprazole (CYP2C19 inhibition)

### 4.2 Duplicate Medication Engine (`duplicate_engine.py`)
- Detects exact duplicates and repeated therapeutic agents across current and active prescriptions.
- Surfaces non-alarming observational notice: *"Multiple entries for the same medication were detected. Verify intended regimen."*

### 4.3 Allergy Safety Engine (`allergy_engine.py`)
- Cross-references prescribed medications with explicitly documented `patient.known_allergies`.
- Checks drug-class allergen cross-reactivity (e.g., Amoxicillin in penicillin allergy, Ibuprofen in NSAID allergy, Glimepiride in sulfa allergy).

### 4.4 Lab-Medication Context Engine (`lab_context_engine.py`)
- Correlates prescribed drugs with recent abnormal observations from Phase 3/4 `clinical_observations`:
  - Metformin in elevated Serum Creatinine / low eGFR
  - Ramipril / Telmisartan in elevated Serum Potassium (Hyperkalemia)
  - Atorvastatin in elevated ALT / AST transaminases
  - Digoxin in low Serum Potassium (Hypokalemia)

### 4.5 Contraindication Engine (`contraindication_engine.py`)
- Evaluates documented chronic conditions (e.g. Peptic Ulcer Disease + NSAIDs).
- Returns `INSUFFICIENT_CONTEXT` when context is absent, never assuming safety.

---

## 5. CDSS Safety Guardrails (`safety_validator.py`)
All safety findings and clinician texts are validated through regex guardrails prohibiting:
- Prescriptive commands (*"prescribe X"*, *"you should take X"*, *"start taking X"*)
- Dosage titrations (*"increase dose to 1000mg"*, *"reduce dose"*)
- Discontinuation commands (*"stop taking X immediately"*)
- Definitive diagnosis claims (*"patient has diabetes"*)
- Causal claims (*"metformin caused elevated creatinine"*)

---

## 6. Database Schema

### 6.1 `prescriptions`
- `id`: String(36), PK
- `patient_id`: String(36), FK(`patients.id`)
- `document_id`: String(36), FK(`medical_documents.id`)
- `prescriber_name`: String(255)
- `prescription_date`: DateTime(timezone=True)
- `source_confidence`: Float
- `status`: String(50) — `ACTIVE`, `EXTRACTED`, `REVIEW_REQUIRED`, `COMPLETED`
- `created_at`, `updated_at`

### 6.2 `prescription_medications`
- `id`: String(36), PK
- `prescription_id`: String(36), FK(`prescriptions.id`)
- `patient_id`: String(36), FK(`patients.id`)
- `raw_medication_name`: String(255)
- `canonical_medication_name`: String(255)
- `generic_name`, `brand_name`: String(255)
- `strength_value`: Float, `strength_unit`: String(50)
- `dosage_form`, `route`, `frequency_code`, `frequency_text`: String
- `dose_quantity`, `duration_value`, `duration_unit`, `instruction_text`: String/Integer/Text
- `is_prn`: Boolean
- `confidence`: Float
- `review_status`: String(50) — `PENDING`, `ACCEPTED`, `MODIFIED`, `REJECTED`
- `reviewed_by`: String(36), `reviewed_at`: DateTime

### 6.3 `medication_safety_findings`
- `id`: String(36), PK
- `patient_id`: String(36), FK(`patients.id`)
- `prescription_id`, `medication_id`: String(36)
- `finding_type`: String(50)
- `severity`: String(50) — `CRITICAL`, `HIGH`, `MODERATE`, `INFO`
- `title`, `description`, `clinical_association`: String/Text
- `evidence`: JSON (Document ID, Medication ID, Rule ID, Lab correlation, Allergy match, Source text)
- `confidence`: Float
- `rule_id`, `rule_version`: String
- `review_status`: String(50) — `PENDING`, `ACCEPTED`, `MODIFIED`, `REJECTED`
- `clinician_note`: Text
- `reviewed_by`, `reviewed_at`: User ID and timestamp

---

## 7. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/medical-documents/{document_id}/prescription-extraction` | Triggers OCR extraction and medication safety analysis |
| `GET` | `/api/v1/medical-documents/{document_id}/prescription` | Retrieves extracted prescription record for document |
| `GET` | `/api/v1/prescriptions/{prescription_id}` | Retrieves prescription details and medications |
| `GET` | `/api/v1/patients/{patient_id}/prescriptions` | Lists paginated prescriptions for patient |
| `GET` | `/api/v1/patients/{patient_id}/medications` | Lists all extracted medications for patient |
| `GET` | `/api/v1/patients/{patient_id}/medication-timeline` | Returns longitudinal medication timeline |
| `POST` | `/api/v1/patients/{patient_id}/medication-safety-analysis` | Executes multi-engine safety analysis |
| `GET` | `/api/v1/patients/{patient_id}/medication-safety-findings` | Lists patient safety alerts (with severity filters) |
| `GET` | `/api/v1/patients/{patient_id}/medication-safety-findings/{id}` | Retrieves specific safety finding |
| `POST` | `/api/v1/medication-safety-findings/{id}/review` | Clinician reviews and signs finding (Accept/Modify/Reject) |
| `GET` | `/api/v1/medication-rules` | Lists all active safety knowledge base rules |

---

## 8. Verification & Benchmarking
Run full test suite:
```powershell
pytest tests/backend/test_prescription_intelligence.py -v
```
Run deterministic correctness benchmark:
```powershell
python scripts/evaluate_prescription_intelligence.py
```
Run full system regression:
```powershell
pytest -v
```
Run frontend build:
```powershell
cd frontend && npm run build
```
