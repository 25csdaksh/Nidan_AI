import hashlib
import io
from typing import Any, Dict, List, Tuple
from PIL import Image
from app.modules.imaging.preprocessing.transforms import (
    apply_contrast_enhancement,
    convert_to_grayscale,
    resize_with_aspect_ratio,
)


class PreprocessingPipeline:
    """
    Versioned, deterministic medical image preprocessing pipeline.
    Guarantees that identical input bytes produce identical output tensors and hashes.
    """

    VERSION = "xray-preprocess-v1"

    def __init__(self, target_size: Tuple[int, int] = (512, 512)):
        self.target_size = target_size

    def process(self, image_bytes: bytes) -> Tuple[bytes, Dict[str, Any], List[List[float]]]:
        """
        Executes standard deterministic sequence:
        1. Decode image bytes
        2. Convert to single-channel Grayscale (L)
        3. Deterministic contrast optimization
        4. Aspect-ratio preserved resize & zero-padding to target_size
        5. Tensor matrix extraction (normalized [0, 1])

        Returns:
        (processed_png_bytes, metadata_dict, normalized_2d_matrix)
        """
        input_hash = hashlib.sha256(image_bytes).hexdigest()

        with Image.open(io.BytesIO(image_bytes)) as raw_img:
            orig_size = raw_img.size
            orig_mode = raw_img.mode

            # Step 1: Grayscale
            gray = convert_to_grayscale(raw_img)
            # Step 2: Auto-contrast
            enhanced = apply_contrast_enhancement(gray)
            # Step 3: Aspect-ratio preserved padding
            standardized = resize_with_aspect_ratio(enhanced, self.target_size, fill_color=0)

            # Export deterministic PNG bytes
            out_buffer = io.BytesIO()
            standardized.save(out_buffer, format="PNG", optimize=False)
            processed_bytes = out_buffer.getvalue()
            output_hash = hashlib.sha256(processed_bytes).hexdigest()

            # Create normalized float grid representation for model tensor input
            # Sample a downsampled 16x16 grid for fast metadata/inspection
            small_preview = standardized.resize((16, 16), Image.Resampling.BOX)
            matrix = [[round(p / 255.0, 4) for p in small_preview.getdata()][i*16:(i+1)*16] for i in range(16)]

            metadata = {
                "pipeline_version": self.VERSION,
                "input_hash": input_hash,
                "output_hash": output_hash,
                "original_dimensions": orig_size,
                "original_color_mode": orig_mode,
                "target_dimensions": self.target_size,
                "color_space": "GRAYSCALE_L",
                "normalization": "MIN_MAX_0_1",
            }

            return processed_bytes, metadata, matrix


_default_pipeline = PreprocessingPipeline()


def get_default_preprocessing_pipeline() -> PreprocessingPipeline:
    return _default_pipeline
