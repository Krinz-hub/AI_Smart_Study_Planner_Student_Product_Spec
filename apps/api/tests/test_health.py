import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_endpoints(async_client: AsyncClient):
    # Test /api/v1/health
    response_v1 = await async_client.get("/api/v1/health")
    assert response_v1.status_code == 200
    data_v1 = response_v1.json()
    assert data_v1["status"] == "ok"
    assert data_v1["service"] == "smart-study-planner"
    assert "version" in data_v1
    assert "timestamp" in data_v1
    assert "X-Request-ID" in response_v1.headers

    # Test root /health
    response_root = await async_client.get("/health")
    assert response_root.status_code == 200
    assert response_root.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "healthy"
    assert data["checks"]["pgvector"] == "installed"
    assert "timestamp" in data
