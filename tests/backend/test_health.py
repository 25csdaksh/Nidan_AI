import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "NIDAN AI"
    assert data["tagline"] == "Intelligent Clinical Insights"
    assert "cdss_disclaimer" in data
    assert "components" in data
    assert "database" in data["components"]
    assert len(data["modules"]) == 11
    assert "auth" in data["modules"]
    assert "ai" in data["modules"]


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "NIDAN AI"
    assert "disclaimer" in data
