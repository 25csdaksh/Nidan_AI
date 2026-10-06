# NIDAN AI — PHASE 7.5 PRETRAINED MODEL VERIFICATION REPORT
## TorchXRayVision DenseNet-121 Pretrained Checkpoint Activation & Real Inference

**Document ID:** `DOC-NIDAN-XRAY-7501`  
**Phase:** 7.5  
**Date:** 2026-10-07  
**Status:** ✅ **VERIFIED & ACTIVATED**  
**Safety Classification:** Assistive Clinical Decision Support System (Non-Diagnostic Software Verification)  

---

## 1. Executive Summary

Phase 7.5 accomplishes the activation, cryptographic verification, and real forward-pass inference execution of the **TorchXRayVision DenseNet-121** deep learning vision model in NIDAN AI without requiring storage-intensive dataset downloads (>40 GB NIH-14). 

Key Outcomes:
1. **Distribution & License Verification**: Upstream package `torchxrayvision==1.5.5` licensed under Apache 2.0. Model checkpoint trained on multi-site combined radiographs (NIH, PC, CheXpert, MIMIC-CXR, Google, OpenI, RSNA).
2. **Minimal Environment Integration**: PyTorch CPU (`torch-2.14.1+cpu`, `torchvision-0.29.1+cpu`, `torchxrayvision-1.5.5`) installed cleanly with zero backend regression.
3. **Cryptographic Integrity**: Checkpoint `densenet121-res224-all.pt` (28,382,008 bytes, 27.07 MB) acquired and verified with SHA-256 checksum `56524913dd16a906422e8d8b66a7a5c46be1d82eb7ac012d8103776f1aa68899`.
4. **Real Inference Execution**: Real forward pass successfully executed producing 18 finite raw logits and probabilities without runtime errors.
5. **Exact 18-to-12 Taxonomy Mapping**: Documented 1:1 direct mapping for all 12 controlled NIDAN conditions; 6 non-target conditions safely isolated as unsupported/excluded.
6. **Zero Silent Fallback**: Confirmed by unit tests (`ModelWeightsNotConfiguredError` and `ModelChecksumMismatchError` enforced).
7. **Regression Suite**: 97/97 Pytest backend suites pass; Next.js 14 frontend build completes with 0 errors.

---

## 2. Official Model Distribution & Architecture Specification

| Parameter | Specification | Verification Evidence |
|---|---|---|
| **Package** | `torchxrayvision` | Version `1.5.5` (PyPI) |
| **Model Class** | `xrv.models.DenseNet` | DenseNet-121 backbone |
| **Checkpoint Identifier** | `densenet121-res224-all` | Official multi-dataset pretrained weights |
| **Total Parameters** | `6,966,034` | Verified via `sum(p.numel() for p in model.parameters())` |
| **Architecture Config** | `growth_rate=32, block_config=(6, 12, 24, 16), num_init_features=64` | Standard TorchXRayVision DenseNet-121 |
| **Input Channels** | `1` (Single-channel Grayscale) | `torch.Size([1, 1, 224, 224])` |
| **Input Resolution** | `224 x 224` pixels | `input_resolution = 224` |
| **Input Normalization** | `[-1024.0, 1024.0]` range | `xrv.datasets.normalize(arr, maxval=255)` |
| **Output Head** | 18 multi-label linear classifier | `self.classifier = nn.Linear(1024, 18)` |
| **Output Activation** | Uncalibrated Sigmoid | Independent multi-label Bernoulli probabilities |
| **Checkpoint Source** | Official GitHub Release v1 | `https://github.com/mlmed/torchxrayvision/releases/download/v1/nih-pc-chex-mimic_ch-google-openi-kaggle-densenet121-d121-tw-lr001-rot45-tr15-sc15-seed0-best.pt` |
| **File Size** | `28,382,008 bytes` (27.07 MB) | Verified on local disk storage |
| **SHA-256 Checksum** | `56524913dd16a906422e8d8b66a7a5c46be1d82eb7ac012d8103776f1aa68899` | Independently verified before and after load |
| **License** | Apache License 2.0 | Joseph Paul Cohen et al., MIDL 2022 |

---

## 3. Environment & Hardware Assessment

- **Python Version**: `3.10.11` (64-bit AMD64 Windows).
- **Compute Hardware**: CPU (Intel x86_64, PyTorch CPU Execution).
- **Available Disk Storage**: 40 GB free space (model checkpoint requires 27.07 MB).
- **Installed Packages**:
  - `torch==2.14.1+cpu`
  - `torchvision==0.29.1+cpu`
  - `torchxrayvision==1.5.5`
  - `scikit-image==0.25.2`
  - `numpy==2.2.6`
  - `scipy==1.15.3`
  - `pillow==10.3.0`

---

## 4. Controlled Label Taxonomy Mapping (18 XRV -> 12 NIDAN)

| Index | TorchXRayVision Label (18) | NIDAN AI Code (12) | Mapping Category | Clinical Interpretation & Governance Rationale |
|---|---|---|---|---|
| 0 | `Atelectasis` | `ATELECTASIS` | **Direct (1:1)** | Subsegmental or lobar volume loss |
| 1 | `Consolidation` | `CONSOLIDATION` | **Direct (1:1)** | Alveolar airspace filling / dense opacity |
| 2 | `Infiltration` | `INFILTRATION` | **Direct (1:1)** | Ill-defined parenchymal density |
| 3 | `Pneumothorax` | `PNEUMOTHORAX` | **Direct (1:1)** | Visceral pleural line with peripheral lucency |
| 4 | `Edema` | `EDEMA` | **Direct (1:1)** | Interstitial / perihilar congestion |
| 5 | `Emphysema` | *(None)* | **Unsupported** | Excluded from NIDAN 12-condition core taxonomy |
| 6 | `Fibrosis` | `FIBROSIS` | **Direct (1:1)** | Reticular interstitial scarring |
| 7 | `Effusion` | `PLEURAL_EFFUSION` | **Direct (1:1)** | Costophrenic angle blunting / fluid meniscus |
| 8 | `Pneumonia` | `PNEUMONIA` | **Direct (1:1)** | Infective bronchopneumonic consolidation |
| 9 | `Pleural_Thickening` | `PLEURAL_THICKENING` | **Direct (1:1)** | Pleural apical/costal thickening |
| 10 | `Cardiomegaly` | `CARDIOMEGALY` | **Direct (1:1)** | Enlarged cardiac silhouette (CTR > 0.5) |
| 11 | `Nodule` | `NODULE` | **Direct (1:1)** | Well-defined round opacity <= 3cm |
| 12 | `Mass` | `MASS` | **Direct (1:1)** | Focal round opacity > 3cm |
| 13 | `Hernia` | *(None)* | **Unsupported** | Excluded from NIDAN 12-condition core taxonomy |
| 14 | `Lung Lesion` | *(None)* | **Unsupported** | Non-specific lesion tag; excluded from core |
| 15 | `Fracture` | *(None)* | **Unsupported** | Skeletal finding; excluded from core |
| 16 | `Lung Opacity` | *(None)* | **Unsupported** | Composite sign; excluded from primary 12 findings |
| 17 | `Enlarged Cardiomediastinum` | *(None)* | **Unsupported** | Excluded from NIDAN 12-condition core taxonomy |

**Integrity Rule:** All 12 NIDAN taxonomy codes are mapped directly 1:1. The 6 unsupported classes are never fabricated or falsely presented as primary predictions.

---

## 5. Real Inference Forward Pass Verification

A forward pass was executed on a standardized de-identified test radiograph:

```
Input Matrix Size: [224, 224] (Grayscale)
Input Dynamic Range: [-1024.0, 1024.0] (Normalized)
Tensor Shape: torch.Size([1, 1, 224, 224])
Inference Device: CPU
Forward Pass Latency: 114 ms
Raw Logits Status: 18/18 Finite (0 NaN, 0 Inf)
```

### Sample Output Logits and Mapped Probabilities

```
Pathology Name                 Raw Logit        Sigmoid Prob       NIDAN Mapped Code
-----------------------------------------------------------------------------------------
Atelectasis                     -2.1208           0.1071           ATELECTASIS
Consolidation                  -12.0430           0.0000           CONSOLIDATION
Infiltration                   -30.5815           0.0000           INFILTRATION
Pneumothorax                   -26.5312           0.0000           PNEUMOTHORAX
Edema                          -15.4326           0.0000           EDEMA
Fibrosis                       -56.2212           0.0000           FIBROSIS
Effusion                         1.5241           0.8211           PLEURAL_EFFUSION
Pneumonia                      -31.8065           0.0000           PNEUMONIA
Pleural_Thickening             -56.0188           0.0000           PLEURAL_THICKENING
Cardiomegaly                   -10.4558           0.0000           CARDIOMEGALY
Nodule                         -35.5762           0.0000           NODULE
Mass                           -48.1501           0.0000           MASS
-----------------------------------------------------------------------------------------
Emphysema (Unsupported)        -23.5624           0.0000           EXCLUDED
Hernia (Unsupported)           -35.0127           0.0000           EXCLUDED
Lung Lesion (Unsupported)      -47.0409           0.0000           EXCLUDED
Fracture (Unsupported)         -24.3604           0.0000           EXCLUDED
Lung Opacity (Unsupported)       5.9528           0.9974           EXCLUDED
Enlarged Cardiomediastinum     -38.0224           0.0000           EXCLUDED
```

---

## 6. Safety, Audit & CDSS Boundaries

> [!IMPORTANT]
> **CDSS TECHNICAL INFERENCE BOUNDARY**
> A successful forward pass on a test radiograph proves **technical inference capability and software integration correctness only**. It does NOT establish clinical diagnostic accuracy, multi-site generalizability, or sensitivity/specificity for patient diagnosis.
> All probabilities represent uncalibrated multi-label scores. Standalone autonomous diagnostic decisions are strictly prohibited.
