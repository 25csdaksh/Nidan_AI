import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_report_upload_and_pipeline_trigger(client: AsyncClient):
    # 1. Create Patient first
    pat_res = await client.post(
        "/api/v1/patients/",
        json={
            "mrn": "MRN-LAB-2001",
            "first_name": "Thomas",
            "last_name": "Anderson",
            "date_of_birth": "1972-03-11",
            "gender": "male",
            "blood_group": "A+",
            "known_allergies": [],
            "chronic_conditions": [],
        },
    )
    assert pat_res.status_code == 201
    patient_id = pat_res.json()["id"]

    # 2. Upload Medical File
    dummy_pdf_content = b"%PDF-1.4 Clinical Diagnostic Blood Panel Report Content"
    files = {
        "file": ("blood_panel_cbc.pdf", dummy_pdf_content, "application/pdf"),
    }
    data = {
        "patient_id": patient_id,
        "document_type": "blood_report",
    }
    upload_res = await client.post("/api/v1/reports/upload", data=data, files=files)
    assert upload_res.status_code == 202
    res_data = upload_res.json()
    assert "report" in res_data
    assert res_data["report"]["file_name"] == "blood_panel_cbc.pdf"
    assert "task_id" in res_data
    report_id = res_data["report"]["id"]

    # 3. Retrieve Report
    get_rep = await client.get(f"/api/v1/reports/{report_id}")
    assert get_rep.status_code == 200
    assert get_rep.json()["checksum_sha256"] is not None

    # 4. Trigger Phase 0 AI Scaffold
    ai_res = await client.post("/api/v1/ai/trigger", json={"report_id": report_id})
    assert ai_res.status_code == 202
    ai_data = ai_res.json()
    assert ai_data["status"] == "PHASE_0_READY"
    assert "insights_payload" in ai_data
