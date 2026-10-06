# Medical Imaging Intelligence — Chest X-Ray Analysis Foundation

## 1. Executive Summary & Clinical Intent

NIDAN AI Medical Imaging Intelligence (Phase 7) provides an assistive, probabilistic, and evidence-grounded Clinical Decision Support System (CDSS) for chest radiographs (X-Rays).

### Clinical Boundary
- **Assistive Decision Support**: Serves exclusively to support licensed physicians and radiologists.
- **Strict Non-Autonomous Operation**: Never independently diagnoses, stages diseases, or issues prescriptive medication orders.
- **Mandatory Clinician Review**: Every neural finding is marked with `PENDING` review status and requires explicit human clinician verification (`ACCEPTED`, `MODIFIED`, or `REJECTED`).
- **Verifiable Evidence Provenance**: Every finding is assigned an immutable evidence ID (`EVID-XRAY-...`), referencing model weights, preprocessing hash, image SHA-256, and localization metadata.

---

## 2. End-to-End Processing Architecture

```
+-------------------------------------------------------------+
| Medical Image Ingestion (PNG / JPEG / DICOM)                |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Security & Format Validator (Magic Bytes, SHA-256, Bounds)  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Image Quality Gate (Contrast, Blur, Exposure, Aspect Ratio) |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Deterministic Preprocessing Pipeline (xray-preprocess-v1)    |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Medical Vision Model Registry & Inference (BaseImagingModel)|
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Calibration & Threshold Normalization (Platt/Temperature)   |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Uncertainty & Explainability Engine (Attention Heatmap/CAM) |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Safety Validator & Evidence Provenance (EVID-XRAY-...)      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Human Clinician Review Workflow (Accept / Modify / Reject)  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Longitudinal Timeline & Doctor AI Copilot Integration       |
+-------------------------------------------------------------+
```

---

## 3. Radiographic Label Taxonomy

NIDAN AI supports a controlled 12-label chest radiographic pattern taxonomy:
1. **Cardiomegaly Pattern**: Cardiac silhouette enlargement (CTR > 0.50).
2. **Pleural Effusion Pattern**: Blunting of costophrenic angles / fluid meniscus.
3. **Atelectasis Pattern**: Subsegmental/lobar volume loss.
4. **Consolidation Pattern**: Alveolar opacification / air bronchograms.
5. **Pulmonary Edema Pattern**: Interstitial/alveolar congestion & Kerley lines.
6. **Pneumothorax Pattern**: Visceral pleural line with absent peripheral markings.
7. **Infiltration Pattern**: Ill-defined parenchymal opacity.
8. **Pulmonary Mass Pattern (>3cm)**: Well-demarcated density > 3 cm.
9. **Pulmonary Nodule Pattern (<=3cm)**: Discrete focal opacity <= 3 cm.
10. **Pneumonia Pattern**: Infectious alveolar/bronchial opacities.
11. **Fibrosis Pattern**: Reticular opacities & volume distortion.
12. **Pleural Thickening Pattern**: Non-dependent pleural margin thickening.
