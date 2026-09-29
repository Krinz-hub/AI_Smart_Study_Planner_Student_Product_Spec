import pytest
from httpx import AsyncClient
from tests.test_student_state import create_authenticated_user


@pytest.mark.asyncio
async def test_relevant_retrieval_and_citations(async_client: AsyncClient):
    """
    CRITICAL TEST: Relevant query returns top evidence with source citations and SUFFICIENT rating.
    """
    user = await create_authenticated_user(async_client, "rag_user")

    doc_content = (
        "Dijkstra's Algorithm and Graph Shortest Paths.\n\n"
        "Dijkstra's algorithm solves the single-source shortest path problem for a graph "
        "with non-negative edge weights. It maintains a priority queue of vertices with their "
        "current shortest distance from the source.\n\n"
        "At each step, the algorithm extracts the vertex with the minimum distance and relaxes "
        "all outgoing edges. The time complexity using a binary min-heap is O((V + E) log V)."
    ).encode("utf-8")

    files = {"file": ("dijkstra.txt", doc_content, "text/plain")}
    await async_client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        files=files,
    )

    search_res = await async_client.post(
        "/api/v1/retrieval/search",
        headers=user["headers"],
        json={"query": "How does Dijkstra algorithm find shortest path?", "limit": 5},
    )
    assert search_res.status_code == 200
    data = search_res.json()
    assert data["sufficiency"] in ("SUFFICIENT", "PARTIAL")
    assert len(data["sources"]) >= 1

    top_source = data["sources"][0]
    assert top_source["source_id"] == "src_1"
    assert top_source["document_title"] == "dijkstra.txt"
    assert "Dijkstra" in top_source["snippet"]
    assert top_source["relevance_score"] > 0.3


@pytest.mark.asyncio
async def test_irrelevant_retrieval(async_client: AsyncClient):
    """
    CRITICAL TEST: Searching for completely unrelated query produces low relevance.
    """
    user = await create_authenticated_user(async_client, "irrel_user")

    doc_content = b"Quantum Mechanics: Schrodinger wave equation and eigenvalues."
    files = {"file": ("quantum.txt", doc_content, "text/plain")}
    await async_client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        files=files,
    )

    search_res = await async_client.post(
        "/api/v1/retrieval/search",
        headers=user["headers"],
        json={"query": "Baking french butter croissants fermentation", "limit": 5},
    )
    assert search_res.status_code == 200
    data = search_res.json()
    assert data["sufficiency"] in ("INSUFFICIENT", "PARTIAL")


@pytest.mark.asyncio
async def test_cross_user_isolation(async_client: AsyncClient):
    """
    CRITICAL TEST: Strict multi-tenant isolation.
    User B must never retrieve or see any chunks from User A's uploaded documents.
    """
    user_a = await create_authenticated_user(async_client, "tenant_a")
    user_b = await create_authenticated_user(async_client, "tenant_b")

    secret_content = b"Proprietary Secret: Project Zephyr uses Quantum Neural Networks."
    files = {"file": ("secret_project.txt", secret_content, "text/plain")}
    await async_client.post(
        "/api/v1/documents/upload",
        headers=user_a["headers"],
        files=files,
    )

    # User B queries for the exact secret term
    search_res = await async_client.post(
        "/api/v1/retrieval/search",
        headers=user_b["headers"],
        json={"query": "Project Zephyr Quantum Neural Networks", "limit": 5},
    )
    assert search_res.status_code == 200
    data = search_res.json()
    # Must NOT return any of User A's data
    assert data["sufficiency"] == "INSUFFICIENT"
    assert len(data["sources"]) == 0


@pytest.mark.asyncio
async def test_insufficient_evidence(async_client: AsyncClient):
    """
    CRITICAL TEST: When user has no documents uploaded, return INSUFFICIENT evidence.
    """
    user = await create_authenticated_user(async_client, "empty_user")

    search_res = await async_client.post(
        "/api/v1/retrieval/search",
        headers=user["headers"],
        json={"query": "Explain TCP congestion control algorithms", "limit": 5},
    )
    assert search_res.status_code == 200
    data = search_res.json()
    assert data["sufficiency"] == "INSUFFICIENT"
    assert len(data["sources"]) == 0


@pytest.mark.asyncio
async def test_conflicting_sources(async_client: AsyncClient):
    """
    CRITICAL TEST: Contradictory statements within the retrieved evidence are classified as CONFLICTING.
    """
    user = await create_authenticated_user(async_client, "conflict_user")

    # Upload document with contradictory statements
    doc_content = (
        "Python GIL Analysis.\n\n"
        "The Python GIL is required for multi-threading in standard CPython runtime.\n\n"
        "In free-threaded Python 3.13, the Python GIL is not required for multi-threading."
    ).encode("utf-8")

    files = {"file": ("gil_conflict.txt", doc_content, "text/plain")}
    await async_client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        files=files,
    )

    search_res = await async_client.post(
        "/api/v1/retrieval/search",
        headers=user["headers"],
        json={"query": "Is Python GIL required for multi-threading?", "limit": 5},
    )
    assert search_res.status_code == 200
    data = search_res.json()
    assert data["sufficiency"] == "CONFLICTING"
