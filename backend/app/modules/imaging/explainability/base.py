import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExplainabilityResult:
    method: str  # GRAD_CAM, ATTENTION_MAP, SALIENCY_MAP, ANATOMICAL_REGION_PRIOR
    model_version: str
    target_label: str
    heatmap_grid: List[List[float]]  # Downsampled 8x8 or 16x16 attention weights
    localization_boxes: List[Dict[str, Any]]
    disclaimer: str
    generated_at: str


class BaseExplainabilityEngine(abc.ABC):
    """
    Abstract interface for model localization and visual explainability.
    """

    @abc.abstractmethod
    def generate_heatmap(
        self,
        image_bytes: bytes,
        target_label: str,
        probability: float,
        model_version: str,
    ) -> ExplainabilityResult:
        pass
