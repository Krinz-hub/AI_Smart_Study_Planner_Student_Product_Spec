import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_not_found_error_format(async_client: AsyncClient):
    response = await async_client.get("/api/v1/nonexistent-route")
    assert response.status_code == 404
    data = response.json()
    # Contract: {"error": {"code": "...", "message": "...", "request_id": "..."}}
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "request_id" in data["error"]
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] == data["error"]["request_id"]


@pytest.mark.asyncio
async def test_custom_request_id_header(async_client: AsyncClient):
    custom_id = "test-custom-request-id-12345"
    response = await async_client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id
