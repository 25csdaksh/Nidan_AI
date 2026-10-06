import io
from typing import Tuple
from PIL import Image, ImageOps


def convert_to_grayscale(img: Image.Image) -> Image.Image:
    """Converts image to single-channel 8-bit grayscale."""
    if img.mode != "L":
        return img.convert("L")
    return img


def apply_contrast_enhancement(img: Image.Image) -> Image.Image:
    """Applies deterministic auto-contrast / histogram equalization."""
    return ImageOps.autocontrast(img, cutoff=1)


def resize_with_aspect_ratio(
    img: Image.Image,
    target_size: Tuple[int, int] = (512, 512),
    fill_color: int = 0,
) -> Image.Image:
    """
    Resizes image to target dimensions while maintaining aspect ratio,
    centering the image on a padded neutral background (deterministic).
    """
    target_w, target_h = target_size
    img_w, img_h = img.size

    scale = min(target_w / img_w, target_h / img_h)
    new_w = max(1, int(img_w * scale))
    new_h = max(1, int(img_h * scale))

    resized_img = img.resize((new_w, new_h), Image.Resampling.BICUBIC)

    canvas = Image.new("L", (target_w, target_h), fill_color)
    paste_x = (target_w - new_w) // 2
    paste_y = (target_h - new_h) // 2
    canvas.paste(resized_img, (paste_x, paste_y))

    return canvas
