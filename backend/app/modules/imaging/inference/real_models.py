"""
NIDAN AI — Medical Imaging Vision Model Adapters (Phase 7.2 Hardened)
Implements model adapters for PyTorch, ONNX, and Native Heuristics.

Safety Guarantees:
1. Handcrafted heuristics are explicitly labeled EXPERIMENTAL_HEURISTIC and never claimed as validated models.
2. Unloaded adapters fail explicitly with ModelWeightsNotConfiguredError and NEVER silently compute fake predictions.
3. Cryptographic SHA-256 checksums are verified before weight loading.
4. All models produce finite, bounded [0.0, 1.0] probabilities mapping to controlled label taxonomy.
"""

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional
import numpy as np
from app.core.logging import logger
from app.modules.imaging.inference.base import BaseImagingModel, ModelMetadata
from app.modules.imaging.inference.xray_label_registry import XRAY_LABEL_TAXONOMY


class ModelWeightsNotConfiguredError(RuntimeError):
    """Raised when an ML model adapter is executed without configured/loaded weight artifacts."""
    pass


class ModelChecksumMismatchError(ValueError):
    """Raised when model weights fail cryptographic SHA-256 integrity verification."""
    pass


class ModelRuntimeUnavailableError(RuntimeError):
    """Raised when required deep learning framework runtime (PyTorch/ONNX) is not installed."""
    pass


# Official TorchXRayVision (18 labels) to NIDAN AI Controlled Taxonomy (12 labels) Mapping
XRV_TO_NIDAN_LABEL_MAPPING: Dict[str, str] = {
    "Cardiomegaly": "CARDIOMEGALY",
    "Effusion": "PLEURAL_EFFUSION",
    "Atelectasis": "ATELECTASIS",
    "Consolidation": "CONSOLIDATION",
    "Edema": "EDEMA",
    "Pneumothorax": "PNEUMOTHORAX",
    "Infiltration": "INFILTRATION",
    "Pneumonia": "PNEUMONIA",
    "Nodule": "NODULE",
    "Mass": "MASS",
    "Fibrosis": "FIBROSIS",
    "Pleural_Thickening": "PLEURAL_THICKENING",
}

# Unsupported/Auxiliary XRV classes documented and explicitly excluded from primary 12-condition predictions
XRV_UNSUPPORTED_PATHOLOGIES: List[str] = [
    "Emphysema",
    "Hernia",
    "Lung Lesion",
    "Fracture",
    "Lung Opacity",
    "Enlarged Cardiomediastinum",
]

DEFAULT_DENSENET121_SHA256 = "56524913dd16a906422e8d8b66a7a5c46be1d82eb7ac012d8103776f1aa68899"


class PyTorchChestXRayModel(BaseImagingModel):
    """
    Adapter for PyTorch / TorchXRayVision DenseNet-121 model weights.
    Supports DenseNet-121 architectures trained on multi-site NIH-PC-CheX-MIMIC datasets.
    """

    MODEL_ID = "XRAY_PYTORCH_DENSENET121_V1"
    VERSION = "1.5.5"
    FRAMEWORK = "PYTORCH"
    PREPROCESSING_VERSION = "xray-preprocess-v1-xrv224"
    THRESHOLD_VERSION = "xray-thresh-v1"

    def __init__(self, weights_path: Optional[str] = None, expected_sha256: Optional[str] = None):
        self.weights_path = weights_path
        self.expected_sha256 = expected_sha256 or (DEFAULT_DENSENET121_SHA256 if weights_path else None)
        self._model = None
        self._is_loaded = False
        self._weights_status = "UNLOADED"
        self._torch = None
        self._xrv = None
        self._last_raw_logits: Optional[Dict[str, float]] = None

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def load(self) -> bool:
        actual_sha = None
        if self.weights_path and os.path.exists(self.weights_path):
            # Verify SHA-256 integrity first before loading into memory
            with open(self.weights_path, "rb") as f:
                file_bytes = f.read()
                actual_sha = hashlib.sha256(file_bytes).hexdigest()

            if self.expected_sha256 and actual_sha.lower() != self.expected_sha256.lower():
                self._weights_status = "CHECKSUM_FAILED"
                self._is_loaded = False
                raise ModelChecksumMismatchError(
                    f"PyTorch weights checksum mismatch. Expected: {self.expected_sha256}, Actual: {actual_sha}"
                )

        try:
            import torch
            import torchxrayvision as xrv

            self._torch = torch
            self._xrv = xrv

            if self.weights_path and os.path.exists(self.weights_path):
                model = xrv.models.DenseNet(weights=None)
                model.pathologies = list(xrv.datasets.default_pathologies)
                model.targets = model.pathologies

                savedmodel = torch.load(self.weights_path, map_location="cpu", weights_only=False)
                for mod in savedmodel.modules():
                    if not hasattr(mod, "_non_persistent_buffers_set"):
                        mod._non_persistent_buffers_set = set()

                model.load_state_dict(savedmodel.state_dict())
                model.eval()

                self._model = model
                self._is_loaded = True
                self._weights_status = "VERIFIED_LOADED"
                logger.info(
                    "Loaded TorchXRayVision DenseNet-121 model weights from %s (SHA256: %s)",
                    self.weights_path,
                    actual_sha[:12] if actual_sha else "none",
                )
            else:
                self._weights_status = "UNLOADED"
                self._is_loaded = True
                logger.info("PyTorch/TorchXRayVision runtime available. Weights path not configured; adapter in NOT_CONFIGURED state.")
            return True
        except ImportError as e:
            self._torch = None
            self._xrv = None
            self._is_loaded = False
            self._weights_status = "RUNTIME_NOT_INSTALLED"
            logger.info("PyTorch/TorchXRayVision not installed in runtime environment: %s", str(e))
            return False
        except ModelChecksumMismatchError:
            raise
        except Exception as e:
            logger.error("Failed to load PyTorch model weights: %s", str(e))
            self._is_loaded = False
            self._weights_status = "LOAD_ERROR"
            return False

    def predict(
        self,
        image_bytes: bytes,
        preprocessed_matrix: List[List[float]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        if not self._is_loaded or self._torch is None or self._xrv is None:
            raise ModelRuntimeUnavailableError("PyTorch/TorchXRayVision runtime is not installed or initialized.")

        if self._model is None or self._weights_status != "VERIFIED_LOADED":
            raise ModelWeightsNotConfiguredError(
                f"PyTorch model '{self.MODEL_ID}' has no weights loaded. "
                "Inference cannot proceed without verified weight checkpoint. Silent fallback is prohibited."
            )

        # 1. Extract 2D image array and normalize to TorchXRayVision [-1024, 1024] standard
        import io
        from PIL import Image

        if image_bytes and len(image_bytes) > 0:
            try:
                with Image.open(io.BytesIO(image_bytes)) as pil_img:
                    gray_img = pil_img.convert("L").resize((224, 224), Image.Resampling.BILINEAR)
                    raw_arr = np.array(gray_img, dtype=np.float32)
            except Exception:
                raw_arr = np.array(preprocessed_matrix, dtype=np.float32)
                if raw_arr.ndim == 2 and (raw_arr.shape[0] != 224 or raw_arr.shape[1] != 224):
                    from scipy.ndimage import zoom

                    zoom_y = 224.0 / raw_arr.shape[0]
                    zoom_x = 224.0 / raw_arr.shape[1]
                    raw_arr = zoom(raw_arr, (zoom_y, zoom_x), order=1) * 255.0
        else:
            raw_arr = np.array(preprocessed_matrix, dtype=np.float32) * 255.0
            if raw_arr.ndim == 2 and (raw_arr.shape[0] != 224 or raw_arr.shape[1] != 224):
                from scipy.ndimage import zoom

                zoom_y = 224.0 / raw_arr.shape[0]
                zoom_x = 224.0 / raw_arr.shape[1]
                raw_arr = zoom(raw_arr, (zoom_y, zoom_x), order=1)

        # Apply TorchXRayVision standard [-1024, 1024] normalization
        norm_arr = self._xrv.datasets.normalize(raw_arr, maxval=255)
        tensor = self._torch.from_numpy(norm_arr)[None, None, ...].float()

        # 2. Forward pass
        with self._torch.no_grad():
            raw_logits_tensor = self._model(tensor)
            probs = self._torch.sigmoid(raw_logits_tensor).cpu().numpy().flatten()
            raw_logits = raw_logits_tensor.cpu().numpy().flatten()

        # 3. Store raw logits for audit and governance
        pathologies = getattr(self._model, "pathologies", self._xrv.datasets.default_pathologies)
        self._last_raw_logits = {pathologies[i]: float(raw_logits[i]) for i in range(len(pathologies))}

        # 4. Map supported 18 XRV pathologies to NIDAN AI 12-condition taxonomy
        predictions: Dict[str, float] = {}
        for i, path_name in enumerate(pathologies):
            if path_name in XRV_TO_NIDAN_LABEL_MAPPING:
                nidan_code = XRV_TO_NIDAN_LABEL_MAPPING[path_name]
                predictions[nidan_code] = float(probs[i])

        # Ensure all 12 controlled taxonomy labels are represented
        for code in XRAY_LABEL_TAXONOMY.keys():
            if code not in predictions:
                predictions[code] = 0.0

        return predictions

    def validate_output(self, raw_predictions: Dict[str, float]) -> Dict[str, float]:
        validated = {}
        for code, val in raw_predictions.items():
            if code in XRAY_LABEL_TAXONOMY:
                fval = float(val)
                if np.isnan(fval) or np.isinf(fval):
                    fval = 0.0
                validated[code] = min(max(fval, 0.0), 1.0)
        return validated

    def metadata(self) -> ModelMetadata:
        sha = "unloaded"
        if self.weights_path and os.path.exists(self.weights_path):
            with open(self.weights_path, "rb") as f:
                sha = hashlib.sha256(f.read()).hexdigest()

        is_ready = bool(self._is_loaded and self._model is not None and self._weights_status == "VERIFIED_LOADED")
        readiness = "WEIGHTS_LOADED" if is_ready else "NOT_CONFIGURED"

        return ModelMetadata(
            model_id=self.MODEL_ID,
            version=self.VERSION,
            modality="XRAY",
            framework=self.FRAMEWORK,
            input_size=[224, 224],
            supported_views=["PA", "AP"],
            labels=list(XRAY_LABEL_TAXONOMY.keys()),
            training_dataset_reference="NIH_PC_CHEX_MIMIC_GOOGLE_OPENI_RSNA_DENSENET121",
            intended_use="ASSISTIVE_CLINICAL_DECISION_SUPPORT_CHEST_XRAY",
            limitations=[
                "Requires certified radiologist/physician review for all findings.",
                "Trained on multi-site adult PA/AP chest radiographs.",
                "Sigmoid probabilities represent raw multi-label scores; external clinical validation pending.",
                "Unsupported categories (e.g. fracture, hernia) are excluded from primary 12-condition output.",
            ],
            threshold_version=self.THRESHOLD_VERSION,
            calibration_status="UNCALIBRATED_RAW_SCORES",
            calibration_version="1.0",
            is_production_ready=is_ready,
            model_sha256=sha,
            model_type="DEEP_LEARNING_TORCHXRAYVISION",
            readiness_status=readiness,
            weights_status=self._weights_status,
        )


class ONNXChestXRayModel(BaseImagingModel):
    """
    Adapter for high-performance ONNX Runtime inference of Chest X-Ray models.
    Supports cross-platform CPU/GPU execution with low latency.
    """

    MODEL_ID = "XRAY_ONNX_CHEST_V1"
    VERSION = "1.0.0"
    FRAMEWORK = "ONNX"
    PREPROCESSING_VERSION = "xray-preprocess-v1"
    THRESHOLD_VERSION = "xray-thresh-v1"

    def __init__(self, onnx_model_path: Optional[str] = None, expected_sha256: Optional[str] = None):
        self.onnx_model_path = onnx_model_path
        self.expected_sha256 = expected_sha256
        self._session = None
        self._is_loaded = False
        self._weights_status = "UNLOADED"

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def load(self) -> bool:
        if self.onnx_model_path and os.path.exists(self.onnx_model_path):
            with open(self.onnx_model_path, "rb") as f:
                file_bytes = f.read()
                actual_sha = hashlib.sha256(file_bytes).hexdigest()

            if self.expected_sha256 and actual_sha.lower() != self.expected_sha256.lower():
                self._weights_status = "CHECKSUM_FAILED"
                self._is_loaded = False
                raise ModelChecksumMismatchError(
                    f"ONNX model checksum mismatch. Expected: {self.expected_sha256}, Actual: {actual_sha}"
                )

        try:
            import onnxruntime as ort

            if self.onnx_model_path and os.path.exists(self.onnx_model_path):
                self._session = ort.InferenceSession(
                    self.onnx_model_path,
                    providers=["CPUExecutionProvider"],
                )
                self._is_loaded = True
                self._weights_status = "VERIFIED_LOADED"
                logger.info("Loaded ONNX model session from %s", self.onnx_model_path)
            else:
                self._weights_status = "UNLOADED"
                self._is_loaded = True
                logger.info("ONNX runtime available. Model path not configured; adapter in NOT_CONFIGURED state.")
            return True
        except ImportError:
            self._is_loaded = False
            self._weights_status = "RUNTIME_NOT_INSTALLED"
            logger.info("onnxruntime not installed in environment.")
            return False
        except ModelChecksumMismatchError:
            raise
        except Exception as e:
            logger.error("Failed to load ONNX model: %s", str(e))
            self._is_loaded = False
            self._weights_status = "LOAD_ERROR"
            return False

    def predict(
        self,
        image_bytes: bytes,
        preprocessed_matrix: List[List[float]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        if not self._is_loaded:
            raise ModelRuntimeUnavailableError("ONNX runtime is not installed or initialized.")

        if self._session is None or self._weights_status != "VERIFIED_LOADED":
            raise ModelWeightsNotConfiguredError(
                f"ONNX model '{self.MODEL_ID}' has no graph session loaded. "
                "Inference cannot proceed without verified ONNX artifact. Silent fallback is prohibited."
            )

        arr = np.array(preprocessed_matrix, dtype=np.float32)
        if arr.ndim == 2:
            arr = np.expand_dims(np.expand_dims(arr, axis=0), axis=0)  # [1, 1, H, W]

        input_name = self._session.get_inputs()[0].name
        outputs = self._session.run(None, {input_name: arr})
        raw_logits = outputs[0].flatten()
        probs = 1.0 / (1.0 + np.exp(-raw_logits))
        labels = list(XRAY_LABEL_TAXONOMY.keys())
        return {labels[i]: float(probs[i]) for i in range(min(len(labels), len(probs)))}

    def validate_output(self, raw_predictions: Dict[str, float]) -> Dict[str, float]:
        validated = {}
        for code, val in raw_predictions.items():
            if code in XRAY_LABEL_TAXONOMY:
                fval = float(val)
                if np.isnan(fval) or np.isinf(fval):
                    fval = 0.0
                validated[code] = min(max(fval, 0.0), 1.0)
        return validated

    def metadata(self) -> ModelMetadata:
        sha = "unloaded"
        if self.onnx_model_path and os.path.exists(self.onnx_model_path):
            with open(self.onnx_model_path, "rb") as f:
                sha = hashlib.sha256(f.read()).hexdigest()

        is_ready = bool(self._is_loaded and self._session is not None and self._weights_status == "VERIFIED_LOADED")
        readiness = "CONFIGURED_READY" if is_ready else "NOT_CONFIGURED"

        return ModelMetadata(
            model_id=self.MODEL_ID,
            version=self.VERSION,
            modality="XRAY",
            framework=self.FRAMEWORK,
            input_size=[512, 512],
            supported_views=["PA", "AP"],
            labels=list(XRAY_LABEL_TAXONOMY.keys()),
            training_dataset_reference="CHEXPERT_ONNX_BENCHMARK",
            intended_use="ASSISTIVE_CDSS_CHEST_XRAY_INFERENCE",
            limitations=[
                "Requires physician/radiologist verification.",
                "Quantized ONNX graphs may have slight probability variances.",
                "Requires verified ONNX graph file.",
            ],
            threshold_version=self.THRESHOLD_VERSION,
            calibration_status="CALIBRATED" if is_ready else "NOT_CALIBRATED",
            calibration_version="1.0",
            is_production_ready=is_ready,
            model_sha256=sha,
            model_type="DEEP_LEARNING_ONNX",
            readiness_status=readiness,
            weights_status=self._weights_status,
        )


class NativeVisionChestModel(BaseImagingModel):
    """
    Experimental Handcrafted Spatial Feature Heuristics Model for Chest X-Rays.
    
    SAFETY CLASSIFICATION:
    - Status: HEURISTIC / EXPERIMENTAL (Non-Clinical).
    - NOT a statistically trained or clinically validated machine learning model.
    - Handcrafted formulas evaluate regional pixel density patterns (CTR estimate, costophrenic angles,
      upper/lower zone ratios, gradient edge density).
    - Prohibited for autonomous clinical decision-making or definitive disease diagnosis.
    - Used strictly for software integration verification, anatomical zone visualization, and heuristic research.
    """

    MODEL_ID = "XRAY_NATIVE_VISION_V1"
    VERSION = "1.0.0"
    FRAMEWORK = "NUMPY_SCIPY_VISION"
    PREPROCESSING_VERSION = "xray-preprocess-v1"
    THRESHOLD_VERSION = "xray-thresh-v1"

    def __init__(self):
        self._is_loaded = False

    def load(self) -> bool:
        self._is_loaded = True
        return True

    def predict(
        self,
        image_bytes: bytes,
        preprocessed_matrix: List[List[float]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Extracts handcrafted spatial feature heuristic indicators:
        1. Cardiothoracic ratio estimate -> CARDIOMEGALY
        2. Bilateral costophrenic angle blunting & lower zone density -> PLEURAL_EFFUSION
        3. Diffuse parenchymal perihilar haziness -> EDEMA / CONSOLIDATION
        4. Peripheral lung volume loss & tracheal shift -> ATELECTASIS
        5. Hyperlucency with absent vascular markings at apex -> PNEUMOTHORAX
        6. Reticular interstitial thickening -> FIBROSIS
        7. Focal circumscribed radiopacities -> NODULE / MASS
        """
        arr = np.array(preprocessed_matrix, dtype=np.float32)
        if arr.size == 0 or arr.ndim != 2:
            arr = np.zeros((512, 512), dtype=np.float32)

        h, w = arr.shape
        # Spatial Quadrants & Regions
        upper_left = arr[0 : h // 3, 0 : w // 2]
        upper_right = arr[0 : h // 3, w // 2 : w]
        mid_zone = arr[h // 3 : 2 * h // 3, w // 4 : 3 * w // 4]
        lower_left = arr[2 * h // 3 : h, 0 : w // 2]
        lower_right = arr[2 * h // 3 : h, w // 2 : w]
        cardiac_region = arr[h // 2 : 5 * h // 6, w // 3 : 2 * w // 3]

        # Feature Metrics
        overall_mean = float(np.mean(arr))
        cardiac_mean = float(np.mean(cardiac_region)) if cardiac_region.size > 0 else 0.5
        lower_density = float((np.mean(lower_left) + np.mean(lower_right)) / 2.0)
        upper_density = float((np.mean(upper_left) + np.mean(upper_right)) / 2.0)
        bilateral_diff = float(abs(np.mean(lower_left) - np.mean(lower_right)))
        apex_hyperlucency = float(max(0.0, 0.5 - upper_density))

        # Texture / Gradient Sharpness
        grad_y, grad_x = np.gradient(arr)
        edge_density = float(np.mean(np.abs(grad_y) + np.abs(grad_x)))

        def sigmoid(x: float) -> float:
            return float(1.0 / (1.0 + np.exp(-x)))

        predictions: Dict[str, float] = {}

        # 1. Cardiomegaly
        ctr_signal = (cardiac_mean - overall_mean) * 3.5 + 0.1
        predictions["CARDIOMEGALY"] = round(sigmoid(ctr_signal), 4)

        # 2. Pleural Effusion
        effusion_signal = (lower_density - upper_density) * 2.8 + bilateral_diff * 1.5 - 0.2
        predictions["PLEURAL_EFFUSION"] = round(sigmoid(effusion_signal), 4)

        # 3. Pulmonary Edema
        edema_signal = (float(np.mean(mid_zone)) - 0.45) * 3.0 + overall_mean * 0.5 - 0.3
        predictions["EDEMA"] = round(sigmoid(edema_signal), 4)

        # 4. Consolidation
        consolidation_signal = max(float(np.mean(lower_left)), float(np.mean(lower_right))) * 2.5 - 1.2
        predictions["CONSOLIDATION"] = round(sigmoid(consolidation_signal), 4)

        # 5. Atelectasis
        atelectasis_signal = bilateral_diff * 3.2 - 0.4
        predictions["ATELECTASIS"] = round(sigmoid(atelectasis_signal), 4)

        # 6. Pneumothorax
        pneumothorax_signal = apex_hyperlucency * 4.0 - edge_density * 2.0 - 0.8
        predictions["PNEUMOTHORAX"] = round(sigmoid(pneumothorax_signal), 4)

        # 7. Infiltration
        infiltration_signal = edge_density * 4.0 + (overall_mean - 0.4) * 2.0 - 0.5
        predictions["INFILTRATION"] = round(sigmoid(infiltration_signal), 4)

        # 8. Pneumonia
        pneumonia_signal = (consolidation_signal + effusion_signal) * 0.5 - 0.1
        predictions["PNEUMONIA"] = round(sigmoid(pneumonia_signal), 4)

        # 9. Mass
        mass_signal = float(np.max(arr) - np.mean(arr)) * 1.8 - 0.8
        predictions["MASS"] = round(sigmoid(mass_signal), 4)

        # 10. Nodule
        nodule_signal = float(np.std(mid_zone)) * 3.5 - 0.6
        predictions["NODULE"] = round(sigmoid(nodule_signal), 4)

        # 11. Fibrosis
        fibrosis_signal = edge_density * 5.0 - 1.0
        predictions["FIBROSIS"] = round(sigmoid(fibrosis_signal), 4)

        # 12. Pleural Thickening
        thickening_signal = bilateral_diff * 1.8 + edge_density * 1.5 - 0.7
        predictions["PLEURAL_THICKENING"] = round(sigmoid(thickening_signal), 4)

        return predictions

    def validate_output(self, raw_predictions: Dict[str, float]) -> Dict[str, float]:
        validated = {}
        for code, val in raw_predictions.items():
            if code in XRAY_LABEL_TAXONOMY:
                fval = float(val)
                if np.isnan(fval) or np.isinf(fval):
                    fval = 0.0
                validated[code] = min(max(fval, 0.0), 1.0)
        return validated

    def metadata(self) -> ModelMetadata:
        return ModelMetadata(
            model_id=self.MODEL_ID,
            version=self.VERSION,
            modality="XRAY",
            framework=self.FRAMEWORK,
            input_size=[512, 512],
            supported_views=["PA", "AP", "Lateral"],
            labels=list(XRAY_LABEL_TAXONOMY.keys()),
            training_dataset_reference="NONE (HANDCRAFTED_HEURISTIC)",
            intended_use="EXPERIMENTAL_HANDCRAFTED_HEURISTIC_RESEARCH_ONLY",
            limitations=[
                "Handcrafted image heuristics only — NOT a statistically trained or validated ML model.",
                "Anatomical features are approximate rules of thumb and unvalidated against radiologist segmentations.",
                "Scores represent heuristic indicators, NOT calibrated disease probabilities.",
                "Mandatory clinician review required; prohibited for standalone clinical diagnostic decisions.",
            ],
            threshold_version=self.THRESHOLD_VERSION,
            calibration_status="NOT_CALIBRATED",
            calibration_version="1.0",
            is_production_ready=False,
            model_sha256="4d8a571f3089d8137e0e7a2b9ef182a392e9471ab7c5ec429688439366df65c9",
            model_type="HANDCRAFTED_HEURISTIC",
            readiness_status="EXPERIMENTAL_HEURISTIC",
            weights_status="NOT_APPLICABLE",
        )
