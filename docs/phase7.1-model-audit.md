# NIDAN AI — PHASE 7.1 MODEL AUDIT REPORT
## Medical Vision Model & Chest X-Ray Inference Audit

**Audit Date:** 2026-10-06  
**Auditor:** Senior Medical AI Architect & ML Systems Engineer  
**Scope:** Investigation of model artifacts, frameworks, weights, training scripts, label taxonomies, and inference runtime in NIDAN AI.

---

## 1. Executive Summary of Audit

An exhaustive audit of the NIDAN AI codebase was conducted to determine the presence, integrity, and status of medical vision models for chest radiograph interpretation.

### Key Findings:
1. **Model Weights & Artifacts**:
   - No pre-trained binary weights (`.pt`, `.pth`, `.onnx`, `.bin`, `.h5`) exist in the repository root or tracking subdirectories.
   - `.gitignore` correctly prevents tracking of raw binary weights and clinical image datasets to maintain git safety and HIPAA data governance.
2. **Existing Inference Architecture**:
   - `backend/app/modules/imaging/inference/base.py`: Clean `BaseImagingModel` abstraction providing `load()`, `predict()`, `validate_output()`, and `metadata()`.
   - `backend/app/modules/imaging/inference/model_registry.py`: Model registry supporting SHA-256 checksum verification, view constraints, and versioning.
   - `backend/app/modules/imaging/inference/predictor.py`: Implements `ChestXRayDeterministicTestModel`, explicitly labeled `DEMO / TEST ONLY` for software integration testing and deterministic CI/CD pipelines.
3. **Environment & Framework Dependencies**:
   - `numpy` (v1.26+), `scipy` (v1.12+), `scikit-learn` (v1.4+), and `pillow` (v10.0+) are active and verified.
   - `torch`, `torchvision`, `onnxruntime`, and `torchxrayvision` are not pre-installed in the default development environment, necessitating pluggable adapters that support optional acceleration runtimes while maintaining robust fallback execution.
4. **Controlled Label Taxonomy**:
   - `backend/app/modules/imaging/inference/xray_label_registry.py` defines 12 standardized chest conditions (`Atelectasis`, `Cardiomegaly`, `Consolidation`, `Edema`, `Pleural Effusion`, `Pneumothorax`, `Infiltration`, `Mass`, `Nodule`, `Pneumonia`, `Fibrosis`, `Pleural Thickening`) mapped to SNOMED CT and RadLex concepts.

---

## 2. Detailed Audit Matrix

| Category | Status | Details |
|---|---|---|
| **Binary Model Weights** | Not Found | No unverified `.pt`/`.onnx` weights committed in repo. |
| **Model Registry** | Verified | `ModelRegistry` in `inference/model_registry.py` with checksum validation. |
| **Inference Interface** | Verified | `BaseImagingModel` in `inference/base.py`. |
| **Active Test Harness** | Verified | `ChestXRayDeterministicTestModel` (Explicitly marked `DEMO / TEST ONLY`). |
| **Preprocessing Pipeline** | Verified | `xray-preprocess-v1` deterministic transforms (grayscale, autocontrast, aspect padding, resize 512x512). |
| **Label Taxonomy** | Verified | 12 standardized labels in `xray_label_registry.py`. |
| **Training Pipeline** | Needs Creation | Dedicated multi-label training & patient-split harness (`scripts/train_xray_model.py`) required. |
| **Evaluation Harness** | Partial | `scripts/evaluate_xray_model.py` exists; requires multi-label AUROC/AUPRC/ECE/Confusion Matrix expansion. |
| **Explainability Engine** | Verified | `explainability/localization.py` generating 12x12 attention grids and bounding boxes. |

---

## 3. Real-World Model Selection Analysis

To transition beyond the test harness while adhering to strict safety and licensing constraints, candidate open-access medical vision architectures were evaluated:

### Candidate 1: TorchXRayVision DenseNet-121 (`densenet121-res224-all`)
- **Architecture**: DenseNet-121 with feature extraction backbone.
- **Dataset**: Trained on NIH ChestX-ray14, CheXpert, PadChest, and MIMIC-CXR (~800,000 radiograph images).
- **License**: Apache 2.0 / Academic Open Source.
- **Strengths**: Gold standard in academic medical imaging; native support for the 12 NIDAN AI target findings.
- **Input Specification**: 1x224x224 or 1x512x512 grayscale tensor, normalized in [-1024, 1024] or standardized [0, 1].

### Candidate 2: ONNX-Exported DenseNet-121 / ResNet-50 Chest Model
- **Architecture**: Quantized / Float32 ONNX graph.
- **Inference Runtime**: `onnxruntime` or CPU native session.
- **License**: Open-source permissible.
- **Strengths**: High throughput, lightweight dependency footprint, no heavy PyTorch compilation overhead.

### Candidate 3: Native NumPy / SciPy High-Dimensional Feature Inference Adapter
- **Architecture**: Linear probed convolutional feature pooling network.
- **Runtime**: Pure NumPy/SciPy (built-in).
- **Strengths**: Zero external heavyweight binary dependencies; 100% portable across all operating systems without CUDA/wheel compilation conflicts.

---

## 4. Architectural Roadmap for Phase 7.1

1. **Pluggable Real Model Adapter Suite**:
   - Implement `PyTorchChestXRayModel` (supporting PyTorch / TorchXRayVision weights).
   - Implement `ONNXChestXRayModel` (supporting ONNX runtime execution).
   - Implement `NumPyFeatureChestModel` (native NumPy vision inference adapter).
2. **Model Registry Expansion**:
   - Register real model adapters in `ModelRegistry` with explicit checksum and status flags (`APPROVED_FOR_TESTING`, `EXPERIMENTAL`, `DEMO_ONLY`).
3. **Reproducible Training Harness**:
   - Create `scripts/train_xray_model.py` with patient-level stratified splitting, multi-label BCE loss with pos_weight, and checkpoint export.
4. **Comprehensive Evaluation Harness**:
   - Update `scripts/evaluate_xray_model.py` with multi-label AUROC, AUPRC, Sensitivity, Specificity, F1, ECE, and confusion matrix calculations.
5. **Safety, Privacy & Documentation**:
   - Maintain strict CDSS boundaries, immutable audit logs, and clear distinction between software verification and clinical validation.
