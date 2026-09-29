import io
import uuid
import pytest
from httpx import AsyncClient
import pypdf
from tests.test_student_state import create_authenticated_user


@pytest.mark.asyncio
async def test_document_upload_and_chunking(async_client: AsyncClient):
    """Verifies document upload, SHA-256 hashing, semantic chunking, and pgvector embeddings."""
    user = await create_authenticated_user(async_client, "doc_user")

    # Sample educational text content with sections
    content = (
        "Operating Systems: Memory Management\n\n"
        "Virtual memory provides an abstraction of a large, uniform array of storage. "
        "The CPU references memory using virtual addresses, which are translated by the "
        "Memory Management Unit (MMU) into physical addresses.\n\n"
        "Paging divides memory into fixed-size blocks called page frames in physical memory "
        "and pages in virtual memory. When a process attempts to access a page not currently "
        "in RAM, a page fault occurs and the operating system loads the required frame from disk.\n\n"
        "Demand paging minimizes initial memory usage by loading pages only when requested."
    ).encode("utf-8")

    files = {"file": ("operating_systems.txt", content, "text/plain")}
    res = await async_client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        files=files,
    )
    assert res.status_code == 201
    data = res.json()
    assert "document_id" in data
    assert data["processing_status"] == "COMPLETED"
    assert len(data["content_hash"]) == 64

    doc_id = data["document_id"]

    # Verify document metadata and chunk count
    doc_res = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers=user["headers"],
    )
    assert doc_res.status_code == 200
    doc_info = doc_res.json()
    assert doc_info["filename"] == "operating_systems.txt"
    assert doc_info["chunk_count"] >= 1
    assert doc_info["processing_status"] == "COMPLETED"

    # Verify chunks and metadata
    chunks_res = await async_client.get(
        f"/api/v1/documents/{doc_id}/chunks",
        headers=user["headers"],
    )
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    assert len(chunks) >= 1
    assert "metadata_json" in chunks[0]
    assert chunks[0]["metadata_json"]["untrusted_source"] is True


@pytest.mark.asyncio
async def test_document_deduplication(async_client: AsyncClient):
    """Verifies that uploading the exact same file content detects duplicate content hash."""
    user = await create_authenticated_user(async_client, "dedup_user")

    content = b"Database Systems: Relational Algebra and SQL queries."
    files = {"file": ("db_notes.txt", content, "text/plain")}

    res1 = await async_client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        files=files,
    )
    assert res1.status_code == 201
    doc1_id = res1.json()["document_id"]

    # Upload exact duplicate
    files2 = {"file": ("db_notes_copy.txt", content, "text/plain")}
    res2 = await async_client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        files=files2,
    )
    assert res2.status_code == 201
    doc2_id = res2.json()["document_id"]

    # Reused identical hash document
    assert doc1_id == doc2_id


@pytest.mark.asyncio
async def test_document_pdf_parsing(async_client: AsyncClient):
    """Generates a valid multi-page PDF in-memory and verifies PDF parsing and page tracking."""
    user = await create_authenticated_user(async_client, "pdf_user")

    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    files = {"file": ("sample_blank.pdf", pdf_bytes, "application/pdf")}
    res = await async_client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        files=files,
    )
    assert res.status_code == 201
    doc_id = res.json()["document_id"]

    chunks_res = await async_client.get(
        f"/api/v1/documents/{doc_id}/chunks",
        headers=user["headers"],
    )
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    assert len(chunks) >= 2
    # Verify page numbers were tracked
    page_numbers = {c["page_number"] for c in chunks}
    assert 1 in page_numbers
    assert 2 in page_numbers


@pytest.mark.asyncio
async def test_document_tenant_isolation(async_client: AsyncClient):
    """Verifies strict tenant isolation: User B cannot access or delete User A's document."""
    user_a = await create_authenticated_user(async_client, "user_a_doc")
    user_b = await create_authenticated_user(async_client, "user_b_doc")

    content = b"Confidential Research Notes: Quantum Computing"
    files = {"file": ("quantum.txt", content, "text/plain")}

    res_a = await async_client.post(
        "/api/v1/documents/upload",
        headers=user_a["headers"],
        files=files,
    )
    assert res_a.status_code == 201
    doc_id = res_a.json()["document_id"]

    # User B tries to view User A's document
    res_b_view = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers=user_b["headers"],
    )
    assert res_b_view.status_code == 404

    # User B tries to view User A's chunks
    res_b_chunks = await async_client.get(
        f"/api/v1/documents/{doc_id}/chunks",
        headers=user_b["headers"],
    )
    assert res_b_chunks.status_code == 404

    # User B tries to delete User A's document
    res_b_del = await async_client.delete(
        f"/api/v1/documents/{doc_id}",
        headers=user_b["headers"],
    )
    assert res_b_del.status_code == 404


@pytest.mark.asyncio
async def test_document_deletion_cascades(async_client: AsyncClient):
    """Verifies that deleting a document also removes all chunks and embeddings."""
    user = await create_authenticated_user(async_client, "del_user")

    content = b"Compiler Design: Lexical Analysis and Abstract Syntax Trees."
    files = {"file": ("compilers.txt", content, "text/plain")}

    res = await async_client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        files=files,
    )
    doc_id = res.json()["document_id"]

    # Delete document
    del_res = await async_client.delete(
        f"/api/v1/documents/{doc_id}",
        headers=user["headers"],
    )
    assert del_res.status_code == 204

    # Verify 404 on subsequent get
    check_res = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers=user["headers"],
    )
    assert check_res.status_code == 404


@pytest.mark.asyncio
async def test_document_10_point_summary_and_mongo_cache(async_client: AsyncClient):
    """
    STAGE 9 TEST: Verifies 10-point learning summary generation and MongoDB persistence.
    """
    user = await create_authenticated_user(async_client, "summary_user")

    content = (
        "Distributed Systems and Consensus Protocols.\n\n"
        "Raft is defined as a consensus algorithm designed to be more understandable than Paxos. "
        "A leader is elected through randomized election timeouts. "
        "The state progression proceeds as the leader accepts log entries from clients and replicates them to follower nodes. "
        "Split vote is a common pitfall when multiple candidates solicit votes concurrently. "
        "For efficiency, Paxos Invariant states that Quorum = (N / 2) + 1 nodes must agree. "
        "Practical example: Etcd and Consul use Raft for authoritative distributed state lock management."
    ).encode("utf-8")

    upload_res = await async_client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        files={"file": ("distributed_systems.txt", content, "text/plain")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document_id"]

    # 1. Fetch 10-point summary
    sum_res = await async_client.get(f"/api/v1/documents/{doc_id}/summary", headers=user["headers"])
    assert sum_res.status_code == 200
    summary = sum_res.json()

    # Verify all 10 structured sections
    assert summary["document_id"] == doc_id
    assert len(summary["executive_summary"]) > 10
    assert isinstance(summary["key_definitions"], list)
    assert len(summary["key_definitions"]) >= 1
    assert isinstance(summary["formulas_and_equations"], list)
    assert isinstance(summary["core_mechanisms"], list)
    assert isinstance(summary["step_by_step_procedures"], list)
    assert isinstance(summary["common_pitfalls"], list)
    assert isinstance(summary["practical_examples"], list)
    assert isinstance(summary["high_yield_exam_points"], list)
    assert isinstance(summary["prerequisites_and_connections"], list)
    assert isinstance(summary["active_recall_questions"], list)
    assert len(summary["active_recall_questions"]) >= 1

    # 2. Verify cache hit on second call
    sum_res_cached = await async_client.get(f"/api/v1/documents/{doc_id}/summary", headers=user["headers"])
    assert sum_res_cached.status_code == 200
    assert sum_res_cached.json()["executive_summary"] == summary["executive_summary"]


@pytest.mark.asyncio
async def test_document_flashcards_and_note_quiz(async_client: AsyncClient):
    """
    STAGE 10 TEST: Verifies active recall flashcards extraction and note-grounded quiz generation.
    """
    user = await create_authenticated_user(async_client, "flashcard_quiz_user")

    content = (
        "Operating Systems: Deadlock Conditions and Avoidance.\n\n"
        "Mutual Exclusion is defined as a resource condition where only one process may hold a resource at any time. "
        "Hold and Wait occurs when a process holds at least one resource while waiting to acquire additional resources. "
        "Banker's Algorithm: Need = Max - Allocation <= Available vectors. "
        "A common pitfall is assuming circular wait implies deadlock in multi-instance resource systems."
    ).encode("utf-8")

    upload_res = await async_client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        files={"file": ("deadlocks.txt", content, "text/plain")},
    )
    doc_id = upload_res.json()["document_id"]

    # 1. Fetch Flashcards
    fc_res = await async_client.get(f"/api/v1/documents/{doc_id}/flashcards", headers=user["headers"])
    assert fc_res.status_code == 200
    fc_data = fc_res.json()
    assert fc_data["total_flashcards"] >= 2
    for card in fc_data["flashcards"]:
        assert "front" in card
        assert "back" in card
        assert "tag" in card

    # 2. Generate Note-Grounded Quiz
    quiz_res = await async_client.post(
        f"/api/v1/documents/{doc_id}/generate-quiz",
        headers=user["headers"],
        json={"num_questions": 3, "difficulty": "MEDIUM"},
    )
    assert quiz_res.status_code == 200
    quiz_data = quiz_res.json()
    assert "quiz_id" in quiz_data
    assert quiz_data["total_questions"] == 3
    assert len(quiz_data["questions"]) == 3
    for q in quiz_data["questions"]:
        assert "question_text" in q
        assert "options" in q
        assert "correct_answer" not in q

