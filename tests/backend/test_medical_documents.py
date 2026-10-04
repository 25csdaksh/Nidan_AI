import io
from PIL import Image
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import create_access_token, UserRole
from app.modules.medical_documents.processor import process_medical_document_task
from app.modules.medical_documents.models import DocumentTypeEnum, ProcessingStatusEnum


def create_sample_pdf(text: str = "Clinical Diagnostic Laboratory Report - Hematology CBC Hemoglobin") -> bytes:
    """Generates a minimal valid binary PDF."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    raw = buf.getvalue()
    if text:
        raw += f"\n% Text: {text}\n".encode("utf-8")
    return raw


def create_sample_image(format: str = "PNG", size: tuple = (200, 200), color: str = "blue") -> bytes:
    """Generates a minimal valid image binary."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_valid_pdf_upload_and_integrity(client: AsyncClient, db_session: AsyncSession):
    # 1. Create Patient
    pat_res = await client.post(
        "/api/v1/patients/",
        json={
            "mrn": "MRN-DOC-001",
            "first_name": "Arthur",
            "last_name": "Dent",
            "date_of_birth": "1978-03-11",
            "gender": "male",
        },
    )
    assert pat_res.status_code == 201
    patient_id = pat_res.json()["id"]

    # 2. Upload valid PDF
    pdf_bytes = create_sample_pdf()
    files = {"file": ("cbc_blood_test.pdf", pdf_bytes, "application/pdf")}
    data = {"patient_id": patient_id, "document_type": "UNKNOWN"}

    res = await client.post("/api/v1/medical-documents", data=data, files=files)
    assert res.status_code == 201
    res_data = res.json()
    doc = res_data["document"]
    assert doc["original_filename"] == "cbc_blood_test.pdf"
    assert doc["mime_type"] == "application/pdf"
    assert doc["processing_status"] == "QUEUED"
    assert len(doc["sha256_hash"]) == 64
    assert res_data["task_id"] is not None
    doc_id = doc["id"]

    # Storage key must be internal and not contain raw path
    assert f"patients/{patient_id}/documents/{doc_id}/original.pdf" == doc["storage_key"]

    # 3. Test background worker processing
    await process_medical_document_task(doc_id, session=db_session)

    # 4. Check Status Endpoint
    status_res = await client.get(f"/api/v1/medical-documents/{doc_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["processing_status"] == "COMPLETED"
    assert status_data["page_count"] >= 1
    assert status_data["processed_at"] is not None


@pytest.mark.asyncio
async def test_valid_image_formats_upload(client: AsyncClient):
    pat_res = await client.post(
        "/api/v1/patients/",
        json={
            "mrn": "MRN-DOC-IMG",
            "first_name": "Ford",
            "last_name": "Prefect",
            "date_of_birth": "1975-01-01",
            "gender": "male",
        },
    )
    patient_id = pat_res.json()["id"]

    # Test PNG
    png_bytes = create_sample_image("PNG")
    res_png = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id, "document_type": "XRAY"},
        files={"file": ("chest_xray.png", png_bytes, "image/png")},
    )
    assert res_png.status_code == 201
    assert res_png.json()["document"]["mime_type"] == "image/png"
    assert res_png.json()["document"]["document_type"] == "XRAY"

    # Test JPEG
    jpeg_bytes = create_sample_image("JPEG")
    res_jpeg = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files={"file": ("usg_scan.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert res_jpeg.status_code == 201
    assert res_jpeg.json()["document"]["mime_type"] == "image/jpeg"

    # Test WEBP
    webp_bytes = create_sample_image("WEBP")
    res_webp = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files={"file": ("scan_image.webp", webp_bytes, "image/webp")},
    )
    assert res_webp.status_code == 201
    assert res_webp.json()["document"]["mime_type"] == "image/webp"


@pytest.mark.asyncio
async def test_security_rejections(client: AsyncClient):
    pat_res = await client.post(
        "/api/v1/patients/",
        json={"mrn": "MRN-SEC-01", "first_name": "Trillian", "last_name": "Astra", "date_of_birth": "1990-02-02", "gender": "female"},
    )
    patient_id = pat_res.json()["id"]

    # 1. Reject Disallowed Extension (.exe)
    res_exe = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files={"file": ("virus.exe", b"MZ\x90\x00executable", "application/octet-stream")},
    )
    assert res_exe.status_code == 415

    # 2. Reject Spoofed Extension (e.g., text file named .pdf)
    res_spoof = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files={"file": ("fake_report.pdf", b"This is plain text and not a PDF", "application/pdf")},
    )
    assert res_spoof.status_code == 415

    # 3. Reject Double Extension (.pdf.exe / .php.jpg)
    res_double = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files={"file": ("report.exe.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert res_double.status_code == 400

    # 4. Reject Empty File (0 bytes)
    res_empty = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert res_empty.status_code == 400

    # 5. Path Traversal Filename Sanitization
    pdf_bytes = create_sample_pdf()
    res_traversal = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files={"file": ("../../etc/passwd.pdf", pdf_bytes, "application/pdf")},
    )
    assert res_traversal.status_code == 201
    assert res_traversal.json()["document"]["original_filename"] == "passwd.pdf"
    assert ".." not in res_traversal.json()["document"]["storage_key"]


@pytest.mark.asyncio
async def test_oversized_file_rejection(client: AsyncClient, monkeypatch):
    # Set MAX_UPLOAD_SIZE_MB to 1 MB for testing
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)

    pat_res = await client.post(
        "/api/v1/patients/",
        json={"mrn": "MRN-SIZE-01", "first_name": "Slartibartfast", "last_name": "Magrathea", "date_of_birth": "1960-01-01", "gender": "male"},
    )
    patient_id = pat_res.json()["id"]

    # 1.5 MB dummy content
    oversized_bytes = b"%PDF-1.4 " + (b"A" * (int(1.5 * 1024 * 1024)))
    res = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files={"file": ("large.pdf", oversized_bytes, "application/pdf")},
    )
    assert res.status_code == 413


@pytest.mark.asyncio
async def test_duplicate_detection(client: AsyncClient):
    pat_res = await client.post(
        "/api/v1/patients/",
        json={"mrn": "MRN-DUP-01", "first_name": "Marvin", "last_name": "Android", "date_of_birth": "1970-05-05", "gender": "other"},
    )
    patient_id = pat_res.json()["id"]

    pdf_bytes = create_sample_pdf("Duplicate Test Report")

    # 1. First Upload
    res1 = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files={"file": ("original_blood.pdf", pdf_bytes, "application/pdf")},
    )
    assert res1.status_code == 201
    doc1 = res1.json()["document"]

    # 2. Second Upload with same file without allow_duplicate flag
    res2 = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id, "allow_duplicate": False},
        files={"file": ("duplicate_blood.pdf", pdf_bytes, "application/pdf")},
    )
    assert res2.status_code == 201
    res2_data = res2.json()
    assert res2_data["duplicate_warning"] is not None
    assert res2_data["duplicate_warning"]["is_duplicate"] is True
    assert res2_data["duplicate_warning"]["existing_document_id"] == doc1["id"]

    # 3. Third Upload with allow_duplicate=True
    res3 = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id, "allow_duplicate": True},
        files={"file": ("duplicate_override.pdf", pdf_bytes, "application/pdf")},
    )
    assert res3.status_code == 201
    assert res3.json()["document"]["id"] != doc1["id"]


@pytest.mark.asyncio
async def test_patient_documents_pagination_and_filters(client: AsyncClient):
    pat_res = await client.post(
        "/api/v1/patients/",
        json={"mrn": "MRN-PAG-01", "first_name": "Zaphod", "last_name": "Beeblebrox", "date_of_birth": "1975-04-01", "gender": "male"},
    )
    patient_id = pat_res.json()["id"]

    # Upload 3 documents with distinct content and modalities
    pdf1 = create_sample_pdf("Hematology CBC Analysis Report 1")
    pdf2 = create_sample_pdf("Prescription Medication Rx Daily 2")
    img_bytes = create_sample_image("PNG")

    await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id, "document_type": "BLOOD_REPORT"},
        files={"file": ("blood1.pdf", pdf1, "application/pdf")},
    )
    await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id, "document_type": "PRESCRIPTION"},
        files={"file": ("rx1.pdf", pdf2, "application/pdf")},
    )
    await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id, "document_type": "XRAY"},
        files={"file": ("xray1.png", img_bytes, "image/png")},
    )

    # List all
    list_res = await client.get(f"/api/v1/patients/{patient_id}/medical-documents?page=1&page_size=10")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 3
    assert len(list_data["items"]) == 3

    # Filter by modality
    filter_res = await client.get(f"/api/v1/patients/{patient_id}/medical-documents?document_type=XRAY")
    assert filter_res.status_code == 200
    assert filter_res.json()["total"] == 1
    assert filter_res.json()["items"][0]["document_type"] == "XRAY"


@pytest.mark.asyncio
async def test_secure_download_and_soft_delete(client: AsyncClient):
    pat_res = await client.post(
        "/api/v1/patients/",
        json={"mrn": "MRN-DL-01", "first_name": "Eddie", "last_name": "Computer", "date_of_birth": "1980-01-01", "gender": "other"},
    )
    patient_id = pat_res.json()["id"]

    pdf_bytes = create_sample_pdf("Confidential Clinical Diagnostic Data")
    up_res = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files={"file": ("confidential.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = up_res.json()["document"]["id"]

    # 1. Secure Download
    dl_res = await client.get(f"/api/v1/medical-documents/{doc_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.content == pdf_bytes
    assert dl_res.headers["content-type"] == "application/pdf"
    assert 'filename="confidential.pdf"' in dl_res.headers["content-disposition"]

    # 2. Soft Delete
    del_res = await client.delete(f"/api/v1/medical-documents/{doc_id}")
    assert del_res.status_code == 200

    # 3. Confirm Document is no longer retrievable
    get_res = await client.get(f"/api/v1/medical-documents/{doc_id}")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_patient_rbac_isolation(client: AsyncClient):
    # Patient A
    pat_a = await client.post(
        "/api/v1/patients/",
        json={"mrn": "MRN-PAT-A", "first_name": "Alice", "last_name": "Smith", "date_of_birth": "1995-01-01", "gender": "female"},
    )
    id_a = pat_a.json()["id"]

    # Patient B
    pat_b = await client.post(
        "/api/v1/patients/",
        json={"mrn": "MRN-PAT-B", "first_name": "Bob", "last_name": "Jones", "date_of_birth": "1994-01-01", "gender": "male"},
    )
    id_b = pat_b.json()["id"]

    # Upload document for Patient A
    pdf_bytes = create_sample_pdf()
    up_res = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": id_a},
        files={"file": ("alice_report.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = up_res.json()["document"]["id"]

    # Token for Patient B
    token_b = create_access_token(
        subject="user_b",
        role=UserRole.PATIENT.value,
        extra_claims={"patient_id": id_b},
    )

    # Patient B attempts to access Patient A's document -> 403 Forbidden
    unauth_get = await client.get(
        f"/api/v1/medical-documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert unauth_get.status_code == 403

    # Patient B attempts to list Patient A's documents -> 403 Forbidden
    unauth_list = await client.get(
        f"/api/v1/patients/{id_a}/medical-documents",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert unauth_list.status_code == 403
