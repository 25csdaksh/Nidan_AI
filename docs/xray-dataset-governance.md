# Chest X-Ray Dataset Governance & Ethical AI Standards

## 1. Governance Principles

Medical vision models in NIDAN AI are governed by strict ethical, privacy, and clinical guidelines:
1. **Zero PHI Leakage**: No identifying patient health information (PHI) is ever retained in training or evaluation datasets.
2. **Deterministic Versioning**: Every dataset, calibration split, and test evaluation cohort is immutable and versioned.
3. **Data Isolation**: Synthetic test images are explicitly labeled `TEST_ONLY` and quarantined from production clinical repositories.

---

## 2. Dataset Metadata & Cohort Specifications

| Attribute | Specification |
| :--- | :--- |
| **Reference Benchmark Cohorts** | NIH ChestX-ray14, CheXpert, PadChest |
| **Modality** | Frontal Chest Radiographs (PA and AP projections) |
| **Labeling Standard** | Radiologist consensus annotations with ground-truth verification |
| **Split Strategy** | Patient-level partitioning (Zero patient leakage across Train / Val / Test) |
| **De-identification** | DICOM Tag Strip (0010 group) & pixel burn-in bounding box removal |
| **Demographic Representation** | Stratified evaluation across age cohorts, biological sexes, and clinical settings |

---

## 3. Limitations & Bias Considerations

- **Pediatric vs Adult**: Model is calibrated for adult thoracic anatomy (> 18 years). Pediatric interpretation requires specialized clinical validation.
- **Portability Artifacts**: Bedside AP portable radiographs exhibit projectional magnification of the cardiac silhouette; thresholds should be adjusted accordingly.
- **Support Devices**: Endotracheal tubes, pacemakers, and surgical clips may influence spatial heatmaps. Human radiologist verification is required.
