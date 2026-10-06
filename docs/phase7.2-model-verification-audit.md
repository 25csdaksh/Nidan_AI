# NIDAN AI — PHASE 7.2 MODEL VERIFICATION & AUDIT REPORT
## Real Chest X-Ray Model Verification, Dataset Validation & Clinical Safety Hardening

**Audit Date:** 2026-10-06  
**Auditor:** Senior Medical AI/ML Engineer & Healthcare Software Safety Architect  
**Classification:** Medical Device Decision Support Verification Audit (Non-Autonomous CDSS)  

---

## 1. Inventory of Registered Models & Checkpoints

An independent audit of the registered models, adapters, and weight artifacts was performed:

| Model ID | Model Type | Implementation Architecture | Weight Checkpoint File | Checksum Status | Dependencies | Readiness Status |
|---|---|---|---|---|---|---|
| `XRAY_CHEST_FOUNDATION_V1` | `TEST_HARNESS` | Deterministic SHA-256 Hash Digest | Not Applicable (In-memory) | Verified Hardcoded | Python Standard Library | `DEMO_TEST_ONLY` |
| `XRAY_NATIVE_VISION_V1` | `HANDCRAFTED_HEURISTIC` | Spatial Quadrant & Density Rules of Thumb | Not Applicable (In-memory) | Verified Hardcoded | NumPy, SciPy | `EXPERIMENTAL_HEURISTIC` |
| `XRAY_PYTORCH_DENSENET121_V1` | `DEEP_LEARNING_PYTORCH` | DenseNet-121 TorchScript Adapter | Not Configured | `UNLOADED` | PyTorch (Optional) | `NOT_CONFIGURED` |
| `XRAY_ONNX_CHEST_V1` | `DEEP_LEARNING_ONNX` | Quantized DenseNet-121 ONNX Graph | Not Configured | `UNLOADED` | ONNX Runtime (Optional) | `NOT_CONFIGURED` |

---

## 2. In-Depth Technical Audit of the Native Vision Engine

### Audit Findings on `NativeVisionChestModel`:
- **Implementation**: Computes spatial quadrant means, cardiothoracic density differences, edge gradients, and applies mathematical sigmoid functions.
- **Scientific Reality**: These formulas represent **handcrafted image processing rules of thumb**, NOT a statistically trained machine learning or deep neural network model.
- **Verification of Clinical Claims**:
  - The cardiothoracic ratio (CTR) signal is estimated from fixed pixel boundaries ($H/2$ to $5H/6$), not radiologist-validated heart-to-thoracic diameter segmentations.
  - The costophrenic angle blunting signal is estimated from lower-zone pixel brightness differences, which can vary with radiograph exposure, patient rotation, or breast tissue density.
- **Hardened Governance Actions Taken**:
  1. Reclassified `model_type` to `HANDCRAFTED_HEURISTIC`.
  2. Reclassified `readiness_status` to `EXPERIMENTAL_HEURISTIC`.
  3. Reclassified `is_production_ready` to `False`.
  4. Reclassified `calibration_status` to `NOT_CALIBRATED`.
  5. UI and API explicitly display: *"Output derived from handcrafted spatial image heuristics. Not a validated statistical or deep learning model. Mandatory clinician verification required."*

---

## 3. Real Inference & Safe Failure Verification

1. **Explicit Errors on Unloaded Checkpoints**:
   - `PyTorchChestXRayModel.predict()` and `ONNXChestXRayModel.predict()` raise `ModelWeightsNotConfiguredError` when called without a verified weight file.
   - **Silent Fallback Prohibited**: The system strictly refuses to generate synthetic pseudo-predictions when deep learning weights are missing.
2. **Cryptographic Checksum Enforcement**:
   - `PyTorchChestXRayModel.load()` and `ONNXChestXRayModel.load()` compute the SHA-256 digest of external weight files prior to memory allocation.
   - If actual hash does not match `expected_sha256`, the loader raises `ModelChecksumMismatchError` and sets `weights_status="CHECKSUM_FAILED"`.
3. **Reproducibility**:
   - Zero-tolerance exact reproducibility verified across repeated inference runs ($P_{run1} \equiv P_{run2}$).
4. **Finite Output Sanity**:
   - All predictions validated against `XRAY_LABEL_TAXONOMY` (12 conditions), clamped to $[0.0, 1.0]$, with `NaN` and `Inf` protection.

---

## 4. Dataset & Label Governance Audit

- **Clinical Dataset Status**: No external multi-gigabyte NIH-14 or CheXpert image datasets are stored in Git (governed by `.gitignore`).
- **Patient Isolation in Training Pipeline**: `scripts/train_xray_model.py` enforces patient-level partition isolation (`train_pids.isdisjoint(val_pids)` and `train_pids.isdisjoint(test_pids)`).
- **Label Alignment**: Controlled 12-condition taxonomy is unified across all adapters (`Atelectasis`, `Cardiomegaly`, `Consolidation`, `Edema`, `Pleural Effusion`, `Pneumothorax`, `Infiltration`, `Mass`, `Nodule`, `Pneumonia`, `Fibrosis`, `Pleural Thickening`).

---

## 5. Evaluation Framework & Four-Tier Governance

`scripts/evaluate_xray_model.py` was updated to enforce the four-tier medical AI governance hierarchy:
- **Tier 1 (Software Metric Correctness)**: All math functions (AUROC, AUPRC, Sensitivity, Specificity, F1, ECE, Brier Score, Confusion Matrix) verified via automated software tests.
- **Tier 2 (Held-Out Dataset Benchmark)**: When executed without a mounted clinical CSV, the tool explicitly outputs: `[CLINICAL EVALUATION STATUS] NOT EVALUATED (No external clinical test dataset CSV supplied)`.
- **Tier 3 (External Multi-Site Generalization)**: Flagged as `NOT YET PERFORMED`.
- **Tier 4 (Clinical Trial & Radiologist Concordance)**: Flagged as `NOT YET PERFORMED`.

---

## 6. Summary of Hardening Actions

1. Handcrafted heuristics labeled `EXPERIMENTAL_HEURISTIC`.
2. Missing weight files fail with explicit runtime errors (no silent fake predictions).
3. SHA-256 weight checksums enforced.
4. Model readiness cleanly decoupled from software test passing status.
5. Frontend PACS viewer updated with prominent status banners.
6. 28 automated tests passing in `tests/backend/test_imaging_intelligence.py` (89 total backend tests).
