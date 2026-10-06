# Medical Imaging Clinical Safety Guardrails & CDSS Principles

## 1. Statutory CDSS Mandate

NIDAN AI operates as an assistive Clinical Decision Support System under Software as a Medical Device (SaMD) risk guidelines:
- **Assistive Decision Support Only**: Algorithmic predictions are probabilistic evidence intended to augment human medical judgment.
- **No Autonomous Diagnostic or Prescriptive Claims**: The software must never issue autonomous diagnoses, drug orders, dosage adjustments, or survival prognoses.

---

## 2. Strict Language Enforcement

| Prohibited Phrasing (Blocked by Safety Validator) | Required Assistive CDSS Phrasing |
| :--- | :--- |
| ❌ "Patient has pneumonia." | ✅ "Model detected a radiographic pattern associated with consolidation/pneumonia." |
| ❌ "Patient definitely has tuberculosis." | ✅ "Model output indicates elevated probability of parenchymal infiltration requiring clinical correlation." |
| ❌ "Patient has lung cancer." | ✅ "Model identified a focal density pattern larger than 3 cm requiring urgent clinician review." |
| ❌ "Start antibiotics immediately." | ✅ [BLOCKED by Safety Validator — Prescriptions strictly reserved for clinicians] |
| ❌ "Disease location in right lower lobe." | ✅ "Model attention/localization visualization." |

---

## 3. Human-in-the-Loop Clinician Review

1. **Review Actions**:
   - **`ACCEPT`**: Clinician confirms agreement with radiographic pattern.
   - **`MODIFY`**: Clinician adjusts severity (e.g. from HIGH to LOW) with documented clinical rationale.
   - **`REJECT`**: Clinician rejects finding (e.g. due to projection artifact or prior history) with mandatory comment.
2. **Immutability Guarantee**:
   - Review updates `ImagingFinding.review_status` and `clinician_comment` while leaving original model output (`probability`, `model_threshold`, `confidence`, `localization_json`) unmodified for auditability.
