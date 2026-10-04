import pytest
from app.core.storage import LocalStorageService


@pytest.mark.asyncio
async def test_local_storage_lifecycle(tmp_path):
    storage = LocalStorageService(root_dir=str(tmp_path))
    assert await storage.is_healthy() is True

    test_content = b"Medical diagnostic document encrypted payload"
    key = "patients/pat_1/test_doc.pdf"

    # Save
    saved_key, checksum, size = await storage.save_file(test_content, key, "application/pdf")
    assert saved_key == key
    assert size == len(test_content)
    assert len(checksum) == 64

    # Read
    read_bytes = await storage.get_file_bytes(key)
    assert read_bytes == test_content

    # Delete
    deleted = await storage.delete_file(key)
    assert deleted is True

    # Confirm deleted
    with pytest.raises(FileNotFoundError):
        await storage.get_file_bytes(key)
