import io
import math
from typing import Any, Dict, List, Tuple
from PIL import Image, ImageFilter, ImageStat
from app.modules.imaging.models import ImageQualityStatusEnum


class ImageQualityGate:
    """
    Image Quality Control Gate for Chest X-Ray pre-inference validation.
    Performs objective mathematical checks on contrast, exposure, blur, and aspect ratio.
    Does NOT make clinical diagnosis claims.
    """

    MIN_ACCEPTABLE_DIMENSION = 128
    MIN_CONTRAST_STD = 12.0
    MIN_CONTRAST_WARNING_STD = 20.0
    EXTREME_DARK_THRESHOLD = 8.0
    EXTREME_BRIGHT_THRESHOLD = 248.0
    LOW_SHARPNESS_THRESHOLD = 15.0

    @classmethod
    def evaluate(cls, image_bytes: bytes) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Assesses image quality on raw bytes.
        Returns (quality_status, issues_list, metrics_dict).
        """
        issues: List[str] = []
        metrics: Dict[str, Any] = {}

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Convert to grayscale for consistent metric evaluation
                gray_img = img.convert("L")
                width, height = gray_img.size
                aspect_ratio = width / max(height, 1)
                
                stat = ImageStat.Stat(gray_img)
                mean_brightness = stat.mean[0]
                std_contrast = stat.stddev[0]
                min_val, max_val = stat.extrema[0]
                dynamic_range = max_val - min_val

                # Estimate sharpness via Laplacian/Edge variance
                edge_img = gray_img.filter(ImageFilter.FIND_EDGES)
                edge_stat = ImageStat.Stat(edge_img)
                sharpness_score = edge_stat.var[0]

                metrics = {
                    "width": width,
                    "height": height,
                    "aspect_ratio": round(aspect_ratio, 3),
                    "mean_brightness": round(mean_brightness, 2),
                    "contrast_std": round(std_contrast, 2),
                    "dynamic_range": dynamic_range,
                    "sharpness_score": round(sharpness_score, 2),
                }

                # 1. Dimension Check
                if width < cls.MIN_ACCEPTABLE_DIMENSION or height < cls.MIN_ACCEPTABLE_DIMENSION:
                    issues.append(f"Image resolution ({width}x{height}) is below minimum diagnostic quality ({cls.MIN_ACCEPTABLE_DIMENSION}x{cls.MIN_ACCEPTABLE_DIMENSION}).")
                    return ImageQualityStatusEnum.QUALITY_REJECTED.value, issues, metrics

                # 2. Aspect Ratio Anomaly
                if aspect_ratio > 3.0 or aspect_ratio < 0.33:
                    issues.append(f"Unusual anatomical aspect ratio ({aspect_ratio:.2f}) indicates severe cropping or distortion.")

                # 3. Dynamic Range / Uniform Blank
                if dynamic_range < 10 or std_contrast < cls.MIN_CONTRAST_STD:
                    issues.append("Image is nearly uniform or blank; insufficient contrast dynamic range for radiographic analysis.")
                    return ImageQualityStatusEnum.QUALITY_REJECTED.value, issues, metrics

                # 4. Extreme Exposure
                if mean_brightness < cls.EXTREME_DARK_THRESHOLD:
                    issues.append("Severe underexposure: image is excessively dark.")
                elif mean_brightness > cls.EXTREME_BRIGHT_THRESHOLD:
                    issues.append("Severe overexposure: image is washed out.")

                # 5. Contrast Warning
                if std_contrast < cls.MIN_CONTRAST_WARNING_STD:
                    issues.append("Suboptimal contrast: radiographic features may have reduced visibility.")

                # 6. Sharpness / Blur Warning
                if sharpness_score < cls.LOW_SHARPNESS_THRESHOLD:
                    issues.append("Low edge sharpness: potential motion blur or heavy compression artifacts detected.")

                if any("Severe" in iss or "below minimum" in iss or "blank" in iss for iss in issues):
                    quality_status = ImageQualityStatusEnum.QUALITY_REJECTED.value
                elif len(issues) > 0:
                    quality_status = ImageQualityStatusEnum.QUALITY_WARNING.value
                else:
                    quality_status = ImageQualityStatusEnum.QUALITY_ACCEPTED.value

                return quality_status, issues, metrics

        except Exception as e:
            issues.append(f"Quality gate error during inspection: {str(e)}")
            return ImageQualityStatusEnum.QUALITY_REJECTED.value, issues, {"error": str(e)}


def assess_image_quality(image_bytes: bytes) -> Tuple[str, List[str], Dict[str, Any]]:
    return ImageQualityGate.evaluate(image_bytes)
