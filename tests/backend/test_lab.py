import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_lab_batch_and_abnormality_detection(client: AsyncClient):
    # 1. Create Patient & Report
    pat_res = await client.post(
        "/api/v1/patients/",
        json={
            "mrn": "MRN-LAB-3001",
            "first_name": "Clara",
            "last_name": "Oswald",
            "date_of_birth": "1992-11-23",
            "gender": "female",
            "known_allergies": [],
            "chronic_conditions": [],
        },
    )
    patient_id = pat_res.json()["id"]

    rep_res = await client.post(
        "/api/v1/reports/upload",
        data={"patient_id": patient_id, "document_type": "blood_report"},
        files={"file": ("cbc.pdf", b"test content", "application/pdf")},
    )
    report_id = rep_res.json()["report"]["id"]

    # 2. Batch Record Lab Analytes
    batch_payload = [
        {
            "patient_id": patient_id,
            "report_id": report_id,
            "panel_name": "CBC",
            "analyte_name": "Hemoglobin",
            "value_numeric": 9.2,  # Low
            "unit": "g/dL",
            "ref_low": 12.0,
            "ref_high": 15.5,
            "is_abnormal": False,
            "is_critical": False,
        },
        {
            "patient_id": patient_id,
            "report_id": report_id,
            "panel_name": "CBC",
            "analyte_name": "Platelets",
            "value_numeric": 250.0,  # Normal
            "unit": "x10^3/uL",
            "ref_low": 150.0,
            "ref_high": 450.0,
            "is_abnormal": False,
            "is_critical": False,
        },
    ]

    lab_res = await client.post("/api/v1/lab/batch", json=batch_payload)
    assert lab_res.status_code == 201
    results = lab_res.json()
    assert len(results) == 2

    # Verify auto-detection of abnormality
    hb = next(r for r in results if r["analyte_name"] == "Hemoglobin")
    assert hb["is_abnormal"] is True
    assert hb["interpretation"] == "LOW"

    # 3. Query Abnormalities
    abnormal_query = await client.get(f"/api/v1/lab/patient/{patient_id}?only_abnormal=true")
    assert abnormal_query.status_code == 200
    abnormal_results = abnormal_query.json()
    assert len(abnormal_results) == 1
    assert abnormal_results[0]["analyte_name"] == "Hemoglobin"
