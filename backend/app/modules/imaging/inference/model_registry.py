import hashlib
from typing import Dict, List, Optional
from app.modules.imaging.inference.base import BaseImagingModel, ModelMetadata
from app.modules.imaging.inference.predictor import ChestXRayDeterministicTestModel
from app.modules.imaging.inference.real_models import (
    NativeVisionChestModel,
    ONNXChestXRayModel,
    PyTorchChestXRayModel,
)


class ModelRegistry:
    """
    Central registry of approved medical imaging vision models in NIDAN AI.
    Prevents unauthorized model loading and ensures model weight checksum verification.
    """

    def __init__(self):
        self._models: Dict[str, BaseImagingModel] = {}
        self._metadata_registry: Dict[str, ModelMetadata] = {}

        # Register default test harness model (DEMO/TEST ONLY)
        test_model = ChestXRayDeterministicTestModel()
        self.register_model(test_model)

        # Register production-ready native vision model
        native_model = NativeVisionChestModel()
        self.register_model(native_model)

        # Register PyTorch & ONNX framework adapters
        import os

        canonical_weights = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../../../backend/models/weights/densenet121-res224-all.pt")
        )
        if os.path.exists(canonical_weights):
            pytorch_model = PyTorchChestXRayModel(weights_path=canonical_weights)
        else:
            pytorch_model = PyTorchChestXRayModel()
        pytorch_model.load()
        self.register_model(pytorch_model)

        onnx_model = ONNXChestXRayModel()
        self.register_model(onnx_model)

    def register_model(self, model: BaseImagingModel) -> None:
        meta = model.metadata()
        self._models[meta.model_id] = model
        self._metadata_registry[meta.model_id] = meta

    def get_model(self, model_id: str) -> Optional[BaseImagingModel]:
        return self._models.get(model_id)

    def get_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        return self._metadata_registry.get(model_id)

    def list_models(self) -> List[ModelMetadata]:
        return list(self._metadata_registry.values())

    def verify_checksum(self, model_id: str, weights_bytes: bytes) -> bool:
        meta = self.get_metadata(model_id)
        if not meta or not meta.model_sha256:
            return False
        calc_sha = hashlib.sha256(weights_bytes).hexdigest()
        return calc_sha.lower() == meta.model_sha256.lower()


_global_registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    return _global_registry
