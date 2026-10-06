# NIDAN AI — PHASE 7.4 DATASET & MODEL SELECTION REPORT
## Real Dataset Acquisition, Deep Learning Model Training & Independent Evaluation

**Document Version:** 1.0.0  
**Phase:** 7.4  
**Date:** 2026-10-06  
**Lead Roles:** Senior Medical Imaging ML Engineer, MLOps Engineer, Healthcare AI Safety Engineer  
**Classification:** MLOps Acquisition, Pretrained Weights Strategy & Data Governance  

---

## 1. Executive Summary

Phase 7.4 evaluates the technical, licensing, compute, and data governance prerequisites for acquiring real chest radiograph datasets and pretrained deep learning models in NIDAN AI.

In strict compliance with healthcare AI safety and repository rules:
- **No Large Unapproved Downloads**: External datasets exceeding repository limits (40–500 GB) are not automatically downloaded.
- **No Fabricated Checkpoints**: PyTorch and ONNX adapters maintain `NOT_CONFIGURED` status until cryptographically authenticated weight checkpoints are mounted.
- **Truthful Governance**: Clinical benchmark performance remains formally documented as `NOT EVALUATED (No external clinical test dataset supplied)`.
- **Zero Silent Fallback**: Unconfigured deep learning adapters explicitly raise `ModelWeightsNotConfiguredError` upon invocation.

---

## 2. Task 1: Readiness & Storage Audit

### 2.1 Hardware and Compute Profile
- **Host Operating System**: Windows 10 (10.0.26200 AMD64)
- **Python Environment**: Python 3.10.11 (64-bit)
- **Host RAM**: 16.0 GB Total (~1.6 GB Free Physical Memory)
- **Available Disk Space**: **40.35 GB Free** (Drive E:)
- **Compute Accelerator**: Integrated Intel Arc Graphics (2 GB Shared VRAM); CPU execution host for standard PyTorch/ONNX workloads. No discrete NVIDIA CUDA GPU detected.

### 2.2 Storage & Compute Feasibility Analysis

| Dataset / Operation | Required Storage | Local Feasibility (40.35 GB Free) | Compute Feasibility (CPU Host) | Recommendation |
|---|---|---|---|---|
| **NIH ChestX-ray14 (Full)** | ~42 GB Tarballs + ~45 GB Extracted (~87 GB total) | **Infeasible** (Exceeds 40.35 GB disk) | Training from scratch infeasible; Evaluation feasible via batch streaming | Mount external storage or stream test subset |
| **CheXpert-v1.0 (Full)** | ~440 GB | **Infeasible** (Exceeds disk) | Infeasible on CPU | Requires dedicated cloud PACS cluster |
| **CheXpert-v1.0-small (Downsampled)** | ~11 GB | **Feasible** on local disk | Fine-tuning slow (~12-24h/epoch); Inference/Eval feasible | Viable candidate for held-out benchmark |
| **TorchXRayVision Pretrained Weights** | ~30 MB (.pt) | **Fully Feasible** | Real-time CPU inference (~150-300 ms per image) | **Recommended Pretrained Foundation** |
| **ONNX Optimized Model** | ~30 MB (.onnx) | **Fully Feasible** | High-throughput CPU inference (~40-80 ms per image) | **Recommended Production Runtime** |

---

## 3. Task 2: Clinical Dataset Options Evaluation

### 3.1 NIH ChestX-ray14
- **Source**: NIH Clinical Center (Wang et al., 2017)
- **Access Requirements**: Open access public download from NIH / Box repository. No credentialed DUA required.
- **License**: CC0 / Public Domain (Permissive clinical and academic research use).
- **Scale**: 112,120 frontal view radiographs from 30,805 unique patients.
- **Patient Identifiers**: Explicit patient IDs embedded in filenames (`00000001_000.png` -> Patient ID `1`). Enables strict patient-level partition isolation.
- **Label Alignment with NIDAN 12-Condition Taxonomy**:

| NIDAN Target Label | NIH ChestX-ray14 Label | Mapping Type | Notes |
|---|---|---|---|
| `ATELECTASIS` | `Atelectasis` | **Direct** | Exact clinical match |
| `CARDIOMEGALY` | `Cardiomegaly` | **Direct** | Exact clinical match |
| `CONSOLIDATION` | `Consolidation` | **Direct** | Exact clinical match |
| `EDEMA` | `Edema` | **Direct** | Exact clinical match |
| `PLEURAL_EFFUSION` | `Effusion` | **Direct** | Terminology alias |
| `PNEUMOTHORAX` | `Pneumothorax` | **Direct** | Exact clinical match |
| `INFILTRATION` | `Infiltration` | **Direct** | Exact clinical match |
| `MASS` | `Mass` | **Direct** | Exact clinical match |
| `NODULE` | `Nodule` | **Direct** | Exact clinical match |
| `PNEUMONIA` | `Pneumonia` | **Direct** | Exact clinical match |
| `FIBROSIS` | `Fibrosis` | **Direct** | Exact clinical match |
| `PLEURAL_THICKENING` | `Pleural_Thickening` | **Direct** | Exact clinical match |
| *(Unmapped)* | `Emphysema`, `Hernia` | *Ignored* | Outside NIDAN 12-label core |

- **Uncertain-Label Policy**: Labels derived via NLP on radiology reports; no explicit `-1` uncertainty flag. Manifests contain binary `0` or `1`.

### 3.2 CheXpert
- **Source**: Stanford AIMI (Irvin et al., 2019)
- **Access Requirements**: User registration and Data Use Agreement (DUA) acceptance on Stanford AIMI portal.
- **License**: Permissive research use agreement (non-commercial clinical evaluation).
- **Scale**: 224,316 radiographs from 65,240 patients.
- **Label Alignment with NIDAN 12-Condition Taxonomy**:
  - *Direct Matches (7)*: `Atelectasis`, `Cardiomegaly`, `Consolidation`, `Edema`, `Pleural Effusion`, `Pneumothorax`, `Pneumonia`.
  - *Approximate / Overlapping (3)*: `Lung Lesion` (~Nodule/Mass), `Lung Opacity` (~Infiltration/Consolidation), `Pleural Other` (~Pleural Thickening).
  - *Unsupported / Missing (1)*: `Fibrosis` (not explicitly categorized in standard CheXpert 14 observations).
- **Uncertain-Label Policy**: Uses `-1` for ambiguous radiologist report mentions. Requires explicit policy handling in NIDAN AI:
  - `U-Zeros`: Treat `-1` as `0` (conservative specificity).
  - `U-Ones`: Treat `-1` as `1` (conservative sensitivity).
  - `U-Mask`: Exclude uncertain labels from loss computation via masked binary cross-entropy (implemented in `scripts/train_xray_model.py`).

### 3.3 Dataset Acquisition Standard Operating Procedure (SOP)

When external storage is provisioned, follow this manual acquisition protocol:

1. **Mount External Volume**: Attach external SSD/NFS storage to `storage_data/datasets/`.
2. **Download Manifest & Archives**:
   ```bash
   # NIH ChestX-ray14 Example:
   # Download Data_Entry_2017.csv and images_001.tar.gz ... images_012.tar.gz
   # Extract images into storage_data/datasets/nih_chestxray14/images/
   ```
3. **Execute Dataset Governance Audit**:
   ```bash
   python scripts/validate_xray_dataset.py \
       --manifest-csv storage_data/datasets/nih_chestxray14/Data_Entry_2017.csv \
       --image-root storage_data/datasets/nih_chestxray14/images/ \
       --uncertain-policy zeros
   ```
4. Verify output indicates: `[OK] DATASET GOVERNANCE VERIFIED: Manifest is clean, patient-isolated, and compliant.`

---

## 4. Task 3: Pretrained Model Options & Adapter Strategy

### 4.1 TorchXRayVision DenseNet-121 (`densenet121-res224-all`)
- **Architecture**: 121-layer DenseNet with single-channel 224x224 input and 18-pathology multi-label sigmoid head.
- **Pretraining Dataset**: Unified joint training on NIH-14, CheXpert, MIMIC-CXR, PadChest, and OpenI (>800,000 images).
- **Input Normalization**: Grayscale image converted to range `[-1024, 1024]` (Hounsfield-like) or `[-1, 1]`.
- **License**: Apache-2.0.
- **Checkpoint Source**: Official Zenodo / GitHub releases (`torchxrayvision` package, ~30 MB).
- **Adapter Integration**: NIDAN AI's [`PyTorchChestXRayModel`](file:///e:/NIDAN_AI/backend/app/modules/imaging/inference/real_models.py) maps the 12 corresponding outputs directly to NIDAN's 12-label taxonomy.

### 4.2 Stanford CheXNet
- **Architecture**: DenseNet-121 initialized on ImageNet and fine-tuned on NIH-14.
- **Input Normalization**: 3-channel RGB `[0.485, 0.456, 0.406]`, `[0.229, 0.224, 0.225]`, 224x224.
- **License**: Stanford Research / MIT.
- **Size**: ~28 MB.

### 4.3 Model Checkpoint Provisioning SOP

To configure real weights in NIDAN AI:

1. **Obtain Official Checkpoint**: Download verified `.pt` or `.onnx` model weights from an authorized repository.
2. **Compute Cryptographic Hash**:
   ```bash
   powershell -Command "Get-FileHash storage_data/models/densenet121_xray.pt -Algorithm SHA256"
   ```
3. **Configure Adapter in Model Registry**:
   Set `weights_path` and `expected_sha256` in [`backend/app/modules/imaging/inference/real_models.py`](file:///e:/NIDAN_AI/backend/app/modules/imaging/inference/real_models.py):
   ```python
   registry.register_model(
       PyTorchChestXRayModel(
           weights_path="storage_data/models/densenet121_xray.pt",
           expected_sha256="<computed_sha256_hash>"
       ),
       is_default=True
   )
   ```
4. **Verify Integrity on Startup**: The adapter automatically computes the runtime SHA-256 on `.load()`. Any checksum mismatch raises `ModelChecksumMismatchError` and prevents inference.

---

## 5. Task 5: Strategy Decision Matrix

| Strategy Path | Technical & Safety Assessment | Decision |
|---|---|---|
| **Path A: Pretrained Model Integration** | Safest and most reproducible option. Avoids training compute bottlenecks while delivering peer-reviewed weights. | **Selected Strategy for Production Staging** |
| **Path B: Fine-Tuning on Patient Splits** | Viable when external GPU cluster and NIH/CheXpert datasets are provisioned. | **Selected Strategy for Future Hospital Tuning** |
| **Path C: Training From Scratch** | Inappropriate for CPU compute and sample efficiency. | **Rejected** |

---

## 6. Truthful Current State Summary

```
+-------------------------------------------------------------------------------+
|                       NIDAN AI PHASE 7.4 STATUS SUMMARY                       |
+-------------------------------------------------------------------------------+
| 1. External Clinical Dataset           | NOT MOUNTED (Requires external drive)|
| 2. Deep Learning Model Weights         | NOT_CONFIGURED (Awaiting mount)      |
| 3. Native Vision Baseline Engine       | EXPERIMENTAL_HEURISTIC (Non-clinical)|
| 4. Test Harness Model                  | DEMO_TEST_ONLY                       |
| 5. Silent Fallback Policy              | STRICTLY PROHIBITED (Explicit Errors)|
| 6. Held-Out Evaluation Benchmark       | NOT EVALUATED                        |
| 7. Software Correctness & CI/CD        | 93/93 Backend Tests Passed (0 errors)|
| 8. Frontend Production Build           | Clean Compilation (0 errors)         |
+-------------------------------------------------------------------------------+
```
