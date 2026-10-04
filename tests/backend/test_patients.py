import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_patient_lifecycle(client: AsyncClient):
    # 1. Create Patient
    payload = {
        "mrn": "MRN-TEST-1001",
        "first_name": "Sarah",
        "last_name": "Connor",
        "date_of_birth": "1985-05-12",
        "gender": "female",
        "blood_group": "B+",
        "phone": "+1-555-0100",
        "email": "sarah.c@example.org",
        "known_allergies": ["Latex", "Iodine"],
        "chronic_conditions": ["Hypertension"],
    }
    create_res = await client.post("/api/v1/patients/", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["mrn"] == "MRN-TEST-1001"
    assert created_data["first_name"] == "Sarah"
    patient_id = created_data["id"]

    # 2. Duplicate MRN Rejection
    dup_res = await client.post("/api/v1/patients/", json=payload)
    assert dup_res.status_code == 400
    assert dup_res.json()["error"]["code"] == "MRN_EXISTS"

    # 3. Retrieve Patient
    get_res = await client.get(f"/api/v1/patients/{patient_id}")
    assert get_res.status_code == 200
    assert get_res.json()["last_name"] == "Connor"

    # 4. Search Patients
    search_res = await client.get("/api/v1/patients/?q=Connor")
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) == 1
    assert results[0]["mrn"] == "MRN-TEST-1001"

    # 5. Patch Patient
    patch_res = await client.patch(
        f"/api/v1/patients/{patient_id}",
        json={"phone": "+1-555-0999"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["phone"] == "+1-555-0999"
