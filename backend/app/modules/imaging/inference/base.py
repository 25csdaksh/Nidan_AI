import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelMetadata:
    model_id: str
    version: str
    modality: str
    framework: str  # PYTORCH, ONNX, TORCHSCRIPT, DETERMINISTIC_TEST_HARNESS, NUMPY_SCIPY_VISION
    input_size: List[int]  # [512, 512]
    supported_views: List[str]  # ["PA", "AP", "Lateral"]
    labels: List[str]
    training_dataset_reference: str
    intended_use: str
    limitations: List[str]
    threshold_version: str
    calibration_status: str  # CALIBRATED, NOT_CALIBRATED, EXPERIMENTAL
    calibration_version: str
    is_production_ready: bool = False
    model_sha256: Optional[str] = None
    model_type: str = "TEST_HARNESS"  # TEST_HARNESS, HANDCRAFTED_HEURISTIC, DEEP_LEARNING_PYTORCH, DEEP_LEARNING_ONNX
    readiness_status: str = "DEMO_TEST_ONLY"  # DEMO_TEST_ONLY, EXPERIMENTAL_HEURISTIC, NOT_CONFIGURED, CONFIGURED_READY
    weights_status: str = "NOT_APPLICABLE"  # NOT_APPLICABLE, UNLOADED, VERIFIED_LOADED, CHECKSUM_FAILED


class BaseImagingModel(abc.ABC):
    """
    Abstract Base Class for Medical Vision Models in NIDAN AI.
    Provides standard lifecycle interface: load, predict, validate_output, and metadata.
    """

    @abc.abstractmethod
    def load(self) -> bool:
        """Loads weights / initializes runtime engine."""
        pass

    @abc.abstractmethod
    def predict(
        self,
        image_bytes: bytes,
        preprocessed_matrix: List[List[float]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Executes model forward pass.
        Returns mapping from label code to raw float probability in [0.0, 1.0].
        """
        pass

    @abc.abstractmethod
    def validate_output(self, raw_predictions: Dict[str, float]) -> Dict[str, float]:
        """Validates bounds, checks NaN/Inf, and verifies registered labels."""
        pass

    @abc.abstractmethod
    def metadata(self) -> ModelMetadata:
        """Returns comprehensive metadata describing model provenance and limitations."""
        pass
