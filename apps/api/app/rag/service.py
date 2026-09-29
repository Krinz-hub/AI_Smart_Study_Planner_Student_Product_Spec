import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.documents.models import Document, DocumentChunk
from app.documents.embeddings import get_embedding_provider
from app.rag.schemas import (
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    SourceCitation,
)
from app.rag.retrieval import (
    RankedCandidate,
    BM25Scorer,
    compute_rrf,
    rerank_candidates,
    classify_evidence_sufficiency,
)
from app.common.logging import get_logger

logger = get_logger("rag_service")


async def search_and_rank(
    db: AsyncSession,
    user_id: uuid.UUID,
    req: RetrievalSearchRequest,
) -> RetrievalSearchResponse:
    """
    Executes tenant-isolated hybrid retrieval:
    pgvector cosine similarity + Okapi BM25 + Reciprocal Rank Fusion + Cross-Reranker + Evidence Sufficiency.
    """
    query = req.query.strip()
    limit = req.limit

    # 1. Fetch user's candidate chunks (STRICT TENANT ISOLATION)
    # Never retrieve across users
    base_stmt = (
        select(DocumentChunk, Document.filename)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.user_id == user_id)
    )
    if req.subject_id:
        base_stmt = base_stmt.where(Document.subject_id == req.subject_id)

    # 2. Vector search (pgvector cosine distance)
    provider = get_embedding_provider()
    query_vector = await provider.embed_query(query)

    vector_stmt = (
        base_stmt.order_by(DocumentChunk.embedding.cosine_distance(query_vector))
        .limit(max(limit * 3, 30))
    )
    vector_res = await db.execute(vector_stmt)
    vector_rows = vector_res.all()
    vector_ranked_ids = [chunk.id for chunk, _ in vector_rows]

    # 3. BM25 Lexical search across user chunks
    # Fetch all candidate texts for user/subject to score with BM25
    all_chunks_res = await db.execute(base_stmt)
    all_chunks_rows = all_chunks_res.all()

    if not all_chunks_rows:
        return RetrievalSearchResponse(
            query=query,
            sufficiency="INSUFFICIENT",
            sources=[],
            total_candidates=0,
        )

    corpus = [(chunk.id, chunk.text) for chunk, _ in all_chunks_rows]
    bm25_scorer = BM25Scorer()
    bm25_scored = bm25_scorer.score_corpus(query, corpus)
    bm25_ranked_ids = [chunk_id for chunk_id, score in bm25_scored if score > 0.0]

    # 4. Reciprocal Rank Fusion (RRF k=60)
    rrf_map = compute_rrf(vector_ranked_ids, bm25_ranked_ids, k=60)

    # Build lookup map for candidates
    chunks_map = {chunk.id: (chunk, filename) for chunk, filename in all_chunks_rows}

    # Gather top candidates by RRF score
    sorted_candidate_ids = sorted(
        rrf_map.keys(),
        key=lambda cid: rrf_map[cid],
        reverse=True,
    )[: max(limit * 2, 20)]

    candidates: List[RankedCandidate] = []
    for cid in sorted_candidate_ids:
        chunk, filename = chunks_map[cid]
        cand = RankedCandidate(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=filename,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            page_number=chunk.page_number,
            section_path=chunk.section_path,
            rrf_score=rrf_map[cid],
        )
        candidates.append(cand)

    # 5. Cross-Reranker scoring
    reranked = rerank_candidates(query, candidates)
    top_candidates = reranked[:limit]

    # 6. Evidence Sufficiency Classification
    sufficiency = classify_evidence_sufficiency(query, top_candidates)

    # 7. Source Citations
    sources: List[SourceCitation] = []
    for i, c in enumerate(top_candidates):
        # Snippet truncation with clean boundary
        snippet = c.text[:280] + ("..." if len(c.text) > 280 else "")
        source = SourceCitation(
            source_id=f"src_{i + 1}",
            document_id=c.document_id,
            document_title=c.document_title,
            page_number=c.page_number,
            section_path=c.section_path,
            chunk_index=c.chunk_index,
            snippet=snippet,
            relevance_score=c.rerank_score,
        )
        sources.append(source)

    logger.info(
        "rag_search_completed",
        user_id=str(user_id),
        query=query,
        sufficiency=sufficiency,
        results_count=len(sources),
    )

    return RetrievalSearchResponse(
        query=query,
        sufficiency=sufficiency,
        sources=sources,
        total_candidates=len(all_chunks_rows),
    )
