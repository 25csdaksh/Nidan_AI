import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_disclaimer_headers_present_on_all_responses(client: AsyncClient):
    """Verify that every response carries mandatory CDSS non-diagnostic headers."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    
    assert "x-cdss-disclaimer" in response.headers
    assert "NIDAN AI provides assistive clinical insights" in response.headers["x-cdss-disclaimer"]
    assert "x-cdss-confidence-policy" in response.headers
    assert "Human-in-the-loop" in response.headers["x-cdss-confidence-policy"]
    assert "x-request-id" in response.headers
    assert "x-response-time-ms" in response.headers
