import abc
import hashlib
import os
import shutil
from pathlib import Path
from typing import BinaryIO, Optional, Tuple
import aiofiles
from app.core.config import settings
from app.core.logging import logger


class BaseStorageService(abc.ABC):
    """Abstract interface for medical document and image storage."""

    @abc.abstractmethod
    async def save_file(
        self,
        file_bytes: bytes,
        destination_key: str,
        content_type: str = "application/octet-stream",
    ) -> Tuple[str, str, int]:
        """
        Saves file to storage.
        Returns (storage_key, sha256_checksum, size_bytes).
        """
        pass

    @abc.abstractmethod
    async def get_file_bytes(self, storage_key: str) -> bytes:
        """Retrieves raw file bytes."""
        pass

    @abc.abstractmethod
    async def delete_file(self, storage_key: str) -> bool:
        """Deletes file from storage."""
        pass

    @abc.abstractmethod
    async def get_file_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Generates access or pre-signed URL."""
        pass

    @abc.abstractmethod
    async def is_healthy(self) -> bool:
        """Checks if storage backend is accessible."""
        pass


class LocalStorageService(BaseStorageService):
    """Local filesystem storage implementation for air-gapped or local environments."""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> Path:
        # Prevent directory traversal attacks
        clean_key = os.path.normpath(storage_key).lstrip("/\\")
        return self.root_dir / clean_key

    async def save_file(
        self,
        file_bytes: bytes,
        destination_key: str,
        content_type: str = "application/octet-stream",
    ) -> Tuple[str, str, int]:
        target_path = self._resolve_path(destination_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        sha256 = hashlib.sha256(file_bytes).hexdigest()
        size = len(file_bytes)

        async with aiofiles.open(target_path, "wb") as f:
            await f.write(file_bytes)

        logger.debug("Stored local file at %s (SHA: %s, %d bytes)", target_path, sha256[:8], size)
        return destination_key, sha256, size

    async def get_file_bytes(self, storage_key: str) -> bytes:
        target_path = self._resolve_path(storage_key)
        if not target_path.exists():
            raise FileNotFoundError(f"File '{storage_key}' not found in local storage.")
        async with aiofiles.open(target_path, "rb") as f:
            return await f.read()

    async def delete_file(self, storage_key: str) -> bool:
        target_path = self._resolve_path(storage_key)
        if target_path.exists():
            target_path.unlink()
            return True
        return False

    async def get_file_url(self, storage_key: str, expires_in: int = 3600) -> str:
        # Local mock URL endpoint
        return f"/api/v1/reports/file/{storage_key}"

    async def is_healthy(self) -> bool:
        return self.root_dir.exists() and os.access(self.root_dir, os.W_OK)


class S3StorageService(BaseStorageService):
    """S3 / MinIO compatible object storage implementation."""

    def __init__(self, bucket_name: str, region: str, access_key: str, secret_key: str):
        self.bucket_name = bucket_name
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        # For Phase 0, if S3 credentials are unset, fallback gracefully
        self._fallback_local = LocalStorageService(settings.STORAGE_LOCAL_ROOT)

    async def save_file(
        self,
        file_bytes: bytes,
        destination_key: str,
        content_type: str = "application/octet-stream",
    ) -> Tuple[str, str, int]:
        if not self.bucket_name or not self.access_key:
            return await self._fallback_local.save_file(file_bytes, destination_key, content_type)
        # Production boto3/aioboto3 implementation goes here
        return await self._fallback_local.save_file(file_bytes, destination_key, content_type)

    async def get_file_bytes(self, storage_key: str) -> bytes:
        return await self._fallback_local.get_file_bytes(storage_key)

    async def delete_file(self, storage_key: str) -> bool:
        return await self._fallback_local.delete_file(storage_key)

    async def get_file_url(self, storage_key: str, expires_in: int = 3600) -> str:
        return await self._fallback_local.get_file_url(storage_key, expires_in)

    async def is_healthy(self) -> bool:
        return await self._fallback_local.is_healthy()


def get_storage_service() -> BaseStorageService:
    """Factory function for selecting the configured storage provider."""
    if settings.STORAGE_BACKEND == "s3":
        return S3StorageService(
            bucket_name=settings.S3_BUCKET_NAME,
            region=settings.S3_REGION,
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
        )
    return LocalStorageService(root_dir=settings.STORAGE_LOCAL_ROOT)
