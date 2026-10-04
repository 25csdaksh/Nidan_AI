import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_registration_and_login(client: AsyncClient):
    # 1. Register Clinician
    reg_payload = {
        "email": "dr.smith@nidan.ai",
        "password": "SecurePassword2026!",
        "full_name": "Dr. John Smith",
        "role": "physician",
        "license_number": "MED-NY-99120",
        "department": "Internal Medicine",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == "dr.smith@nidan.ai"
    assert "hashed_password" not in user_data

    # 2. Login
    login_payload = {
        "email": "dr.smith@nidan.ai",
        "password": "SecurePassword2026!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user"]["full_name"] == "Dr. John Smith"

    # 3. Invalid Credentials
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "dr.smith@nidan.ai", "password": "WrongPassword"},
    )
    assert bad_login.status_code == 401
