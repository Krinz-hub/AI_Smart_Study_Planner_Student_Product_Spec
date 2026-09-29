import pytest
from httpx import AsyncClient
from tests.test_student_state import create_authenticated_user


@pytest.mark.asyncio
async def test_web_search_and_caching(async_client: AsyncClient):
    """Verifies web research search provider and caching functionality."""
    user = await create_authenticated_user(async_client, "research_user")

    query = "Dynamic Programming Knapsack"
    res1 = await async_client.post(
        "/api/v1/research/search",
        headers=user["headers"],
        json={"query": query, "limit": 3},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1["results"]) >= 1
    assert data1["query"] == query

    # Immediate second query must hit cache
    res2 = await async_client.post(
        "/api/v1/research/search",
        headers=user["headers"],
        json={"query": query, "limit": 3},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["provider"] == "cache"
    assert len(data2["results"]) == len(data1["results"])


@pytest.mark.asyncio
async def test_ssrf_protection_blocks_private_networks(async_client: AsyncClient):
    """
    CRITICAL SECURITY TEST: Strict SSRF protection must reject attempts
    to access localhost, private subnets, and cloud metadata endpoints.
    """
    user = await create_authenticated_user(async_client, "ssrf_test_user")

    blocked_targets = [
        "http://127.0.0.1:8000/api/v1/health",
        "http://localhost:5432",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1/admin",
        "http://192.168.1.1/router",
        "http://172.16.0.5:8080",
    ]

    for target in blocked_targets:
        res = await async_client.post(
            "/api/v1/research/fetch",
            headers=user["headers"],
            json={"url": target},
        )
        assert res.status_code == 403
        err = res.json()["error"]
        assert "SSRF Protection" in err["message"]


@pytest.mark.asyncio
async def test_ssrf_blocks_non_http_protocols(async_client: AsyncClient):
    """Verifies that non-HTTP/HTTPS protocols are blocked."""
    user = await create_authenticated_user(async_client, "proto_test_user")

    invalid_protocols = [
        "file:///etc/passwd",
        "ftp://internal.example.com/data",
        "gopher://example.com",
    ]

    for target in invalid_protocols:
        res = await async_client.post(
            "/api/v1/research/fetch",
            headers=user["headers"],
            json={"url": target},
        )
        assert res.status_code == 403
