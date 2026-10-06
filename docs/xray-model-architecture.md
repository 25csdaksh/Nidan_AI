# Chest X-Ray Model Architecture & Inference Pipeline

## 1. Vision Model Abstraction (`BaseImagingModel`)

NIDAN AI defines a modular vision model interface preventing hardcoded dependencies on specific neural architectures or ML frameworks.

```python
class BaseImagingModel(abc.ABC):
    @abc.abstractmethod
    def load(self) -> bool: ...

    @abc.abstractmethod
    def predict(
        self,
        image_bytes: bytes,
        preprocessed_matrix: List[List[float]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]: ...

    @abc.abstractmethod
    def validate_output(self, raw_predictions: Dict[str, float]) -> Dict[str, float]: ...

    @abc.abstractmethod
    def metadata(self) -> ModelMetadata: ...
```

---

## 2. Model Registry & Version Tracking

The `ModelRegistry` maintains active version metadata, checksum verification (`model_sha256`), and execution parameters.

- **Active Model Identifier**: `XRAY_CHEST_FOUNDATION_V1`
- **Model Version**: `1.0.0`
- **Modality**: `XRAY` (Thoracic Radiography)
- **Framework Compatibility**: `ONNX`, `TorchScript`, `PyTorch`, and `DETERMINISTIC_TEST_HARNESS`
- **Standard Preprocessing**: `xray-preprocess-v1` (Grayscale, CLAHE/autocontrast, 512x512 aspect-ratio padding, [0,1] normalization)
- **Threshold Version**: `xray-thresh-v1`
- **Calibration Engine**: `TEMPERATURE_SCALING` (T = 1.15)

---

## 3. Calibration & Uncertainty Engine

Raw model logit probabilities are calibrated using temperature scaling:
$$P_{calibrated} = \sigma\left(\frac{\text{logit}(P_{raw})}{T}\right)$$

### Uncertainty Boundary Decision
- If $|P_{calibrated} - \text{Threshold}| \le 0.06$, the finding status is flagged as **`UNCERTAIN`**.
- The UI highlights borderline confidence to prompt prioritized clinician verification.

---

## 4. Explainability & Attention Heatmaps

- **Localization Method**: Grad-CAM / Attention Grid overlay (12x12 normalized spatial weights).
- **Bounding Boxes**: Bounded prior regions for mediastinum/cardiac, pleura, and lung parenchyma.
- **CDSS Language Rule**: Strictly designated as *"Model attention/localization visualization"* and never as *"Disease boundary"*.
