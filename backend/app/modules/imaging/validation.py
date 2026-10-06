import hashlib
import io
import os
import re
from typing import Optional, Set, Tuple
from PIL import Image, ImageOps
from fastapi import HTTPException, status
from app.core.logging import logger

MAX_IMAGE_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "application/dicom",
    "application/octet-stream",  # often used for raw DICOM
}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".dcm", ".dicom"}
MIN_DIMENSION = 64
MAX_DIMENSION = 8192

# Magic Byte Signatures
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC_1 = b"\xff\xd8\xff"
DICOM_MAGIC = b"DICM"  # At byte offset 128


class MedicalImageValidationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class MedicalImageSecurityError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def sanitize_filename(filename: str) -> str:
    """Removes path traversal characters and normalizes filename."""
    base = os.path.basename(filename)
    clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    clean = re.sub(r"\.\.+", ".", clean)
    if not clean or clean.startswith("."):
        clean = f"image_{clean.lstrip('.')}"
    return clean[:200]


def detect_file_format_and_magic(file_bytes: bytes, filename: str) -> str:
    """
    Validates magic bytes against allowed medical image formats.
    Returns format identifier: 'PNG', 'JPEG', 'DICOM' or raises exception.
    """
    if len(file_bytes) < 8:
        raise MedicalImageValidationError("File is truncated or too small to be a valid image.")

    if file_bytes.startswith(PNG_MAGIC):
        return "PNG"
    if file_bytes.startswith(JPEG_MAGIC_1):
        return "JPEG"
    
    # DICOM has 128-byte preamble followed by 'DICM'
    if len(file_bytes) >= 132 and file_bytes[128:132] == DICOM_MAGIC:
        return "DICOM"

    # Some raw DICOM files have no preamble and start with group/element tags
    ext = os.path.splitext(filename.lower())[1]
    if ext in {".dcm", ".dicom"} and len(file_bytes) > 256:
        # Check standard DICOM transfer syntax or preamble
        return "DICOM"

    raise MedicalImageValidationError(
        "Invalid file magic bytes. Expected valid PNG, JPEG, or DICOM medical image format."
    )


def validate_and_inspect_image(
    file_bytes: bytes,
    original_filename: str,
    mime_type: Optional[str] = None,
) -> Tuple[str, str, int, int, int, str]:
    """
    Strictly validates upload:
    - File size limits
    - Filename hygiene & path traversal protection
    - Magic bytes format check
    - Image parsing & decompression verification
    - Dimensions within reasonable bounds
    - Bit depth & color space

    Returns:
    (format, sha256_hash, width, height, bit_depth, color_space)
    """
    # 1. Size Validation
    file_size = len(file_bytes)
    if file_size == 0:
        raise MedicalImageValidationError("Uploaded file is empty (0 bytes).")
    if file_size > MAX_IMAGE_FILE_SIZE_BYTES:
        raise MedicalImageValidationError(
            f"Image file size ({file_size / (1024*1024):.1f} MB) exceeds maximum permitted limit (50 MB)."
        )

    # 2. Extension check
    clean_name = sanitize_filename(original_filename)
    ext = os.path.splitext(clean_name.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise MedicalImageValidationError(
            f"Disallowed file extension '{ext}'. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 3. Magic Bytes Detection
    fmt = detect_file_format_and_magic(file_bytes, clean_name)

    # 4. SHA-256 Hash
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # 5. Image Structure / Decompression Integrity
    if fmt in ["PNG", "JPEG"]:
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                img.verify()  # Verifies file integrity
            # Reopen for metadata inspection because verify() closes/invalidates the image
            with Image.open(io.BytesIO(file_bytes)) as img:
                width, height = img.size
                mode = img.mode
                if width < MIN_DIMENSION or height < MIN_DIMENSION:
                    raise MedicalImageValidationError(
                        f"Image dimensions ({width}x{height}) are below minimum diagnostic threshold ({MIN_DIMENSION}x{MIN_DIMENSION})."
                    )
                if width > MAX_DIMENSION or height > MAX_DIMENSION:
                    raise MedicalImageValidationError(
                        f"Image dimensions ({width}x{height}) exceed maximum allowable bounds ({MAX_DIMENSION}x{MAX_DIMENSION})."
                    )
                
                bit_depth = 16 if mode in ("I;16", "I;16B", "I;16L", "I") else 8
                color_space = "GRAYSCALE" if mode in ("L", "I;16", "I", "1") else "RGB"
        except Exception as e:
            if isinstance(e, MedicalImageValidationError):
                raise
            logger.warning("Corrupted or malformed image rejected: %s", str(e))
            raise MedicalImageValidationError(f"Image decompression failed or payload is corrupted: {str(e)}")
    elif fmt == "DICOM":
        from app.modules.imaging.dicom import parse_dicom_metadata_and_dimensions
        width, height, bit_depth, color_space = parse_dicom_metadata_and_dimensions(file_bytes)
        if width < MIN_DIMENSION or height < MIN_DIMENSION:
            raise MedicalImageValidationError(
                f"DICOM image dimensions ({width}x{height}) are below minimum diagnostic threshold ({MIN_DIMENSION}x{MIN_DIMENSION})."
            )
    else:
        raise MedicalImageValidationError(f"Unsupported format {fmt}")

    return fmt, sha256_hash, width, height, bit_depth, color_space
