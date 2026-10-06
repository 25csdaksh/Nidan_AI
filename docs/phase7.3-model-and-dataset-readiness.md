# NIDAN AI — PHASE 7.3 DATA AND COMPUTE READINESS REPORT
## Real Chest X-Ray Deep Learning Model Training, Integration & Evaluation

**Audit Date:** 2026-10-06  
**Auditor:** Senior Medical Imaging ML Engineer & Healthcare Software Safety Architect  
**Classification:** MLOps & Compute Readiness Audit (Non-Autonomous CDSS)  

---

## 1. Data Availability & Governance Status

| Dataset Candidate | Size | Provenance / Source | License | Local Status in Workspace |
|---|---|---|---|---|
| **NIH ChestX-ray14** | ~42 GB (112,120 images) | NIH Clinical Center | Public Domain / CC0 | `NOT_MOUNTED` (Requires external storage bucket) |
| **CheXpert** | ~440 GB (224,316 images) | Stanford AIMI | Permissive Research Use | `NOT_MOUNTED` (Requires DUA sign-off) |
| **MIMIC-CXR** | ~500 GB (377,110 images) | PhysioNet / BIDMC | PhysioNet Credentialed | `NOT_MOUNTED` (Requires CITI certification) |
| **Synthetic Test Partitions** | < 1 MB | NIDAN AI Software Harness | MIT / Internal | `AVAILABLE` (For CI/CD software verification only) |

**Conclusion on Datasets:**  
No multi-gigabyte clinical radiograph images or patient PACS data are committed in Git. In accordance with healthcare data governance and git safety rules, training on external clinical populations is formally marked as `BLOCKED (EXTERNAL_DATASET_NOT_MOUNTED)`.

---

## 2. Compute Environment & Hardware Specs

- **Operating System**: Windows 10 (10.0.26200 AMD64)
- **Python Runtime**: Python 3.10.11 (64-bit)
- **Available Disk Space**: 40.36 GB Free (Drive E:)
- **Active ML Packages**: `numpy` (v1.26+), `scipy` (v1.12+), `scikit-learn` (v1.4+), `pillow` (v10.0+)
- **Deep Learning Frameworks**:
  - `torch` / `torchvision`: Optional acceleration runtime (not pre-installed in default lightweight test environment).
  - `onnxruntime`: Optional high-throughput runtime (not pre-installed in default lightweight test environment).
- **GPU Acceleration**: None (CPU Execution Host).

---

## 3. Model Adapter Interface & Taxonomy Mapping

NIDAN AI defines a controlled, unified 12-condition chest radiograph taxonomy mapped to RadLex and SNOMED CT:

```python
LABELS = [
    "ATELECTASIS",        # RadLex: RID49527
    "CARDIOMEGALY",       # RadLex: RID49533
    "CONSOLIDATION",      # RadLex: RID49535
    "EDEMA",              # RadLex: RID49538
    "PLEURAL_EFFUSION",   # RadLex: RID49544
    "PNEUMOTHORAX",       # RadLex: RID49547
    "INFILTRATION",       # RadLex: RID49540
    "MASS",               # RadLex: RID49542
    "NODULE",             # RadLex: RID49543
    "PNEUMONIA",          # RadLex: RID49546
    "FIBROSIS",           # RadLex: RID49539
    "PLEURAL_THICKENING"  # RadLex: RID49545
]
```

All 4 registered model classes (`PyTorchChestXRayModel`, `ONNXChestXRayModel`, `NativeVisionChestModel`, `ChestXRayDeterministicTestModel`) strictly preserve this label order and output dimension (12 logits/probabilities).

---

## 4. Evaluation of Model Strategy Options (Task 2)

### Option A: Fine-tune Pretrained Chest X-Ray Model (Recommended for Production Staging)
- **Approach**: Load pretrained DenseNet-121 weights trained on public NIH-14 / CheXpert, freeze lower convolutional blocks, and fine-tune classifier heads.
- **Advantages**: Requires significantly less compute (5–10 epochs vs 100+ epochs from scratch), achieves $>0.82$ AUROC on public benchmarks, well-documented in literature (Rajpurkar et al., 2017).
- **Licensing**: Apache 2.0 / Permissive Academic.
- **Prerequisites**: Requires provisioning validated `.pt` or `.onnx` weight checkpoint with verified SHA-256 hash.

### Option B: Train Multi-Label Classifier From Scratch
- **Approach**: Train 121-layer DenseNet or ResNet from random initialization.
- **Disadvantages**: Scientifically inappropriate for local workstation compute. Requires 100,000+ training radiographs, multi-GPU CUDA nodes, and weeks of compute. High risk of overfitting.

### Option C: Governed Safe Readiness & MLOps Tooling (Selected for Current Phase)
- **Approach**: Maintain training blocked until authorized clinical PACS datasets are mounted, while implementing full MLOps data validation tooling (`scripts/validate_xray_dataset.py`), patient-split verification, class-imbalance positive weighting, early stopping, and checkpoint manifest generators.
- **Advantages**: 100% truthful, prevents fabricating fake clinical metrics, guarantees zero silent fallbacks.

---

## 5. Prerequisites Checklist for Full Clinical Training

| Prerequisite | Status | Action Required |
|---|---|---|
| **Python Environment & Preprocessing** | Ready | `xray-preprocess-v1` verified and deterministic |
| **Model Registry & Checksum Verification** | Ready | Enforced in `ModelRegistry` and `real_models.py` |
| **Dataset Validation Tooling** | Ready | `scripts/validate_xray_dataset.py` implemented |
| **Reproducible Training Harness** | Ready | `scripts/train_xray_model.py` with patient-level splits |
| **Five-Tier Evaluation Suite** | Ready | `scripts/evaluate_xray_model.py` implemented |
| **Clinical Dataset Manifest (CSV + Images)** | Blocked | Awaiting external PACS cohort mount |
| **Validated PyTorch / ONNX Checkpoint** | Blocked | Awaiting approved weight file provisioning |
| **Multi-Site Clinical Efficacy Trial** | Blocked | Prospective clinical study required |
