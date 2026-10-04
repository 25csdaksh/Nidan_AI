import io
import os
import re
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
from pypdf import PdfReader
from app.core.config import settings
from app.core.errors import AppException


class FileValidationError(AppException):
    def __init__(self, message: str, code: str = "FILE_VALIDATION_ERROR", status_code: int = 400):
        super().__init__(message=message, code=code, status_code=status_code)


class FileSecurityValidator:
    """Multi-layered medical document security and integrity validator."""

    # Dangerous extensions to reject immediately
    DISALLOWED_EXTENSIONS = {
        ".exe", ".bat", ".cmd", ".sh", ".py", ".pl", ".rb", ".js", ".ts",
        ".dll", ".so", ".dylib", ".msi", ".vbs", ".ps1", ".jar", ".com",
        ".scr", ".bin", ".elf", ".php", ".phtml", ".asp", ".aspx", ".jsp",
    }

    # Magic byte signatures
    MAGIC_SIGNATURES = {
        "application/pdf": [b"%PDF-"],
        "image/png": [b"\x89PNG\r\n\x1a\n"],
        "image/jpeg": [b"\xff\xd8\xff"],
        "image/webp": [b"RIFF"],  # WEBP requires 'RIFF' at 0 and 'WEBP' at 8
    }

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitizes filename and blocks path traversal attempts."""
        if not filename or not isinstance(filename, str):
            raise FileValidationError("A valid filename must be provided.")

        # Check for null bytes and control chars
        if "\x00" in filename or any(ord(c) < 32 for c in filename):
            raise FileValidationError("Filename contains forbidden control characters or null bytes.")

        # Check for path traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            # Strip out path components, but flag if maliciously formed
            clean_name = os.path.basename(filename.replace("\\", "/"))
            if clean_name != filename:
                # Detected traversal syntax
                filename = clean_name

        clean_name = Path(filename).name
        if not clean_name or clean_name in (".", ".."):
            raise FileValidationError("Invalid or empty filename after path normalization.")

        # Check for double extension attacks (e.g. doc.pdf.exe)
        parts = clean_name.lower().split(".")
        if len(parts) > 2:
            for part in parts[1:-1]:
                if f".{part}" in cls.DISALLOWED_EXTENSIONS:
                    raise FileValidationError(f"Forbidden compound executable extension detected: '.{part}'")

        return clean_name

    @classmethod
    def detect_real_mime_type(cls, file_bytes: bytes) -> Optional[str]:
        """Detects actual MIME type from binary file signature (magic bytes)."""
        if not file_bytes or len(file_bytes) < 4:
            return None

        # Check PDF signature (%PDF-)
        if file_bytes.startswith(b"%PDF-") or (b"%PDF-" in file_bytes[:1024]):
            return "application/pdf"

        # Check PNG signature
        if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"

        # Check JPEG signature
        if file_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"

        # Check WEBP signature (RIFF....WEBP)
        if len(file_bytes) >= 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
            return "image/webp"

        return None

    @classmethod
    def validate_document(
        cls,
        file_bytes: bytes,
        original_filename: str,
        client_mime_type: Optional[str] = None,
    ) -> Tuple[str, str, int]:
        """
        Performs full multi-layer security validation.
        Returns (sanitized_filename, validated_mime_type, file_size_bytes).
        """
        # 1. Size Validation
        size_bytes = len(file_bytes)
        if size_bytes == 0:
            raise FileValidationError("The uploaded file is empty (0 bytes).")

        max_allowed_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if size_bytes > max_allowed_bytes:
            raise FileValidationError(
                f"File size exceeds the maximum limit of {settings.MAX_UPLOAD_SIZE_MB} MB. (Uploaded: {round(size_bytes / (1024 * 1024), 2)} MB)",
                code="FILE_TOO_LARGE",
                status_code=413,
            )

        # 2. Filename & Extension Sanitization
        sanitized_name = cls.sanitize_filename(original_filename)
        ext = Path(sanitized_name).suffix.lower()

        if ext in cls.DISALLOWED_EXTENSIONS:
            raise FileValidationError(f"File extension '{ext}' is prohibited for security reasons.", status_code=415)

        if ext not in settings.ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}",
                status_code=415,
            )

        # 3. Magic Bytes / Real MIME Detection
        real_mime = cls.detect_real_mime_type(file_bytes)
        if not real_mime or real_mime not in settings.ALLOWED_MIME_TYPES:
            raise FileValidationError(
                "File signature does not match any allowed medical document format (PDF, PNG, JPG, WEBP).",
                code="UNSUPPORTED_MEDIA_TYPE",
                status_code=415,
            )

        # 4. Consistency Check between Extension and Magic Bytes
        expected_ext_map = {
            "application/pdf": [".pdf"],
            "image/png": [".png"],
            "image/jpeg": [".jpg", ".jpeg"],
            "image/webp": [".webp"],
        }
        if ext not in expected_ext_map.get(real_mime, []):
            raise FileValidationError(
                f"Extension '{ext}' does not match real file content format '{real_mime}'.",
                status_code=400,
            )

        # 5. Malformed Structure Verification
        if real_mime == "application/pdf":
            try:
                stream = io.BytesIO(file_bytes)
                reader = PdfReader(stream)
                # Ensure at least 1 page or readable metadata
                if len(reader.pages) < 1:
                    raise FileValidationError("PDF contains no valid pages.")
            except Exception as e:
                raise FileValidationError(f"Malformed or corrupted PDF document: {str(e)}")
        else:
            # Image structural check
            try:
                stream = io.BytesIO(file_bytes)
                with Image.open(stream) as img:
                    img.verify()
            except Exception as e:
                raise FileValidationError(f"Malformed or corrupted medical image: {str(e)}")

        return sanitized_name, real_mime, size_bytes
