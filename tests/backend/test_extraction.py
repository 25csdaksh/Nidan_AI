import io
import pytest
from httpx import AsyncClient
from pypdf import PdfWriter
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token



def create_mock_cbc_pdf_bytes() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    # We create a valid PDF with text streams
    # pypdf PdfWriter can write a basic PDF
    buf = io.BytesIO()
    writer.write(buf)
    
    # We craft a valid synthetic PDF with text stream for testing
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 380 >>\nstream\n"
        b"BT\n/F1 12 Tf\n50 700 Td\n(CLINICAL LABORATORY REPORT - COMPLETE BLOOD COUNT) Tj\n"
        b"0 -30 Td\n(Hemoglobin 14.2 g/dL   Reference: 13.0 - 17.0 g/dL) Tj\n"
        b"0 -20 Td\n(WBC Count 7.5 10^3/uL   Reference: 4.0 - 11.0) Tj\n"
        b"0 -20 Td\n(Platelet Count 250 10^3/uL   Reference: 150 - 450) Tj\n"
        b"0 -20 Td\n(Serum Creatinine 0.9 mg/dL   Reference: 0.6 - 1.2 mg/dL) Tj\n"
        b"0 -20 Td\n(Fasting Blood Sugar 95 mg/dL   Reference: 70 - 99 mg/dL) Tj\n"
        b"0 -20 Td\n(Total Cholesterol 180 mg/dL   Reference: < 200 mg/dL) Tj\n"
        b"0 -20 Td\n(TSH 2.4 uIU/mL   Reference: 0.4 - 4.2) Tj\n"
        b"ET\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000676 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n755\n%%EOF"
    )
    return pdf_content


def create_abnormal_pdf_bytes() -> bytes:
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 280 >>\nstream\n"
        b"BT\n/F1 12 Tf\n50 700 Td\n(LABORATORY FINDINGS) Tj\n"
        b"0 -30 Td\n(Hb 8.2 g/dL   Reference: 13.0 - 17.0 g/dL) Tj\n"
        b"0 -20 Td\n(Glucose 240 mg/dL   Reference: 70 - 140 mg/dL) Tj\n"
        b"0 -20 Td\n(Vitamin D 18 ng/mL) Tj\n"
        b"ET\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000576 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n655\n%%EOF"
    )
    return pdf_content


@pytest.mark.asyncio
async def test_full_ocr_extraction_and_entity_parsing(client: AsyncClient, db_session: AsyncSession):
    token = create_access_token(subject="doctor_1", role="PHYSICIAN")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Patient
    patient_res = await client.post(
        "/api/v1/patients/",
        json={
            "first_name": "Aarav",
            "last_name": "Mehta",
            "mrn": "MRN-EXTRACT-001",
            "date_of_birth": "1988-04-15",
            "gender": "male",
            "blood_group": "B+",
        },
        headers=headers,
    )
    assert patient_res.status_code == 201
    patient_id = patient_res.json()["id"]

    # 2. Ingest Document
    pdf_bytes = create_mock_cbc_pdf_bytes()
    files = {"file": ("cbc_panel_report.pdf", pdf_bytes, "application/pdf")}
    data = {"patient_id": patient_id, "document_type": "BLOOD_REPORT"}

    upload_res = await client.post("/api/v1/medical-documents", data=data, files=files, headers=headers)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document"]["id"]

    # 3. Trigger & Run Extraction
    from app.modules.medical_documents.service import MedicalDocumentService

    service = MedicalDocumentService(db_session)
    extraction = await service.execute_document_extraction(doc_id)
    await db_session.commit()

    assert extraction is not None
    assert extraction.page_count >= 1

    # 4. Query Extracted Entities Endpoint
    entities_res = await client.get(
        f"/api/v1/medical-documents/{doc_id}/extraction/entities",
        headers=headers,
    )
    assert entities_res.status_code == 200
    entities_data = entities_res.json()
    items = entities_data["items"]
    assert len(items) >= 5

    # Verify specific canonical extractions
    canonical_map = {item["canonical_name"]: item for item in items}

    assert "Hemoglobin" in canonical_map
    hb = canonical_map["Hemoglobin"]
    assert hb["numeric_value"] == 14.2
    assert hb["normalized_unit"] == "g/dL"
    assert hb["reference_min"] == 13.0
    assert hb["reference_max"] == 17.0
    assert hb["technical_status"] == "WITHIN_REPORTED_RANGE"
    assert hb["confidence"] > 0.85
    assert hb["page_number"] == 1
    assert "Hemoglobin 14.2" in hb["source_text"]

    assert "WBC" in canonical_map
    wbc = canonical_map["WBC"]
    assert wbc["numeric_value"] == 7.5
    assert wbc["normalized_unit"] == "10^3/uL"
    assert wbc["technical_status"] == "WITHIN_REPORTED_RANGE"

    assert "Creatinine" in canonical_map
    creat = canonical_map["Creatinine"]
    assert creat["numeric_value"] == 0.9
    assert creat["normalized_unit"] == "mg/dL"

    assert "TSH" in canonical_map
    tsh = canonical_map["TSH"]
    assert tsh["numeric_value"] == 2.4


@pytest.mark.asyncio
async def test_abnormal_reported_ranges_and_missing_range(client: AsyncClient, db_session: AsyncSession):
    token = create_access_token(subject="doctor_1", role="PHYSICIAN")
    headers = {"Authorization": f"Bearer {token}"}

    patient_res = await client.post(
        "/api/v1/patients/",
        json={
            "first_name": "Sunita",
            "last_name": "Patel",
            "mrn": "MRN-EXTRACT-002",
            "date_of_birth": "1975-09-20",
            "gender": "female",
            "blood_group": "O+",
        },
        headers=headers,
    )
    patient_id = patient_res.json()["id"]

    pdf_bytes = create_abnormal_pdf_bytes()
    files = {"file": ("abnormal_report.pdf", pdf_bytes, "application/pdf")}
    upload_res = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files=files,
        headers=headers,
    )
    doc_id = upload_res.json()["document"]["id"]

    from app.modules.medical_documents.service import MedicalDocumentService

    service = MedicalDocumentService(db_session)
    await service.execute_document_extraction(doc_id)
    await db_session.commit()

    entities_res = await client.get(
        f"/api/v1/medical-documents/{doc_id}/extraction/entities",
        headers=headers,
    )
    items = entities_res.json()["items"]
    canonical_map = {item["canonical_name"]: item for item in items}

    # Hemoglobin 8.2 with range 13.0 - 17.0 should be BELOW_REPORTED_RANGE
    assert "Hemoglobin" in canonical_map
    assert canonical_map["Hemoglobin"]["technical_status"] == "BELOW_REPORTED_RANGE"

    # Glucose 240 with range 70 - 140 should be ABOVE_REPORTED_RANGE
    assert "Glucose" in canonical_map
    assert canonical_map["Glucose"]["technical_status"] == "ABOVE_REPORTED_RANGE"

    # Vitamin D 18 without explicit range in report should be UNKNOWN
    assert "Vitamin D" in canonical_map
    assert canonical_map["Vitamin D"]["technical_status"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_clinician_review_and_audit(client: AsyncClient, db_session: AsyncSession):
    token = create_access_token(subject="doctor_1", role="PHYSICIAN")
    headers = {"Authorization": f"Bearer {token}"}

    patient_res = await client.post(
        "/api/v1/patients/",
        json={
            "first_name": "Rohan",
            "last_name": "Shah",
            "mrn": "MRN-EXTRACT-003",
            "date_of_birth": "1992-01-10",
            "gender": "male",
            "blood_group": "A+",
        },
        headers=headers,
    )
    patient_id = patient_res.json()["id"]

    pdf_bytes = create_mock_cbc_pdf_bytes()
    upload_res = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files={"file": ("report_review.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    doc_id = upload_res.json()["document"]["id"]

    from app.modules.medical_documents.service import MedicalDocumentService

    service = MedicalDocumentService(db_session)
    await service.execute_document_extraction(doc_id)
    await db_session.commit()

    entities_res = await client.get(
        f"/api/v1/medical-documents/{doc_id}/extraction/entities",
        headers=headers,
    )
    entities = entities_res.json()["items"]
    hb_entity = next(e for e in entities if e["canonical_name"] == "Hemoglobin")

    # 1. Clinician Edits Value
    patch_res = await client.patch(
        f"/api/v1/medical-documents/{doc_id}/extraction/entities/{hb_entity['id']}",
        json={
            "review_status": "EDITED",
            "reviewed_value": "14.4",
            "reviewed_unit": "g/dL",
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated_hb = patch_res.json()
    assert updated_hb["review_status"] == "EDITED"
    assert updated_hb["reviewed_value"] == "14.4"
    assert updated_hb["reviewed_by"] == "doctor_1"
    assert updated_hb["reviewed_at"] is not None

    # 2. Clinician Accepts Another Entity
    wbc_entity = next(e for e in entities if e["canonical_name"] == "WBC")
    patch_wbc = await client.patch(
        f"/api/v1/medical-documents/{doc_id}/extraction/entities/{wbc_entity['id']}",
        json={"review_status": "ACCEPTED"},
        headers=headers,
    )
    assert patch_wbc.status_code == 200
    assert patch_wbc.json()["review_status"] == "ACCEPTED"


@pytest.mark.asyncio
async def test_extraction_idempotency_and_retry(client: AsyncClient, db_session: AsyncSession):
    token = create_access_token(subject="doctor_1", role="PHYSICIAN")
    headers = {"Authorization": f"Bearer {token}"}

    patient_res = await client.post(
        "/api/v1/patients/",
        json={
            "first_name": "Meera",
            "last_name": "Joshi",
            "mrn": "MRN-EXTRACT-004",
            "date_of_birth": "1995-07-22",
            "gender": "female",
        },
        headers=headers,
    )
    patient_id = patient_res.json()["id"]

    pdf_bytes = create_mock_cbc_pdf_bytes()
    upload_res = await client.post(
        "/api/v1/medical-documents",
        data={"patient_id": patient_id},
        files={"file": ("report_retry.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    doc_id = upload_res.json()["document"]["id"]

    from app.modules.medical_documents.service import MedicalDocumentService

    service = MedicalDocumentService(db_session)
    # First extraction run
    ext1 = await service.execute_document_extraction(doc_id)
    assert ext1.extraction_version == 1
    await db_session.commit()

    # Second extraction run (retry)
    ext2 = await service.execute_document_extraction(doc_id)
    assert ext2.extraction_version == 2
    await db_session.commit()

    # Verify entities count is not duplicated
    entities_res = await client.get(
        f"/api/v1/medical-documents/{doc_id}/extraction/entities",
        headers=headers,
    )
    entities = entities_res.json()["items"]
    # Hemoglobin should appear exactly once
    hb_count = sum(1 for e in entities if e["canonical_name"] == "Hemoglobin")
    assert hb_count == 1


