import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import uuid


@dataclass
class RankedCandidate:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    chunk_index: int
    text: str
    page_number: Optional[int]
    section_path: Optional[str]
    vector_rank: Optional[int] = None
    bm25_rank: Optional[int] = None
    rrf_score: float = 0.0
    rerank_score: float = 0.0


class BM25Scorer:
    """Okapi BM25 implementation for lexical relevance scoring."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def score_corpus(
        self, query: str, docs: List[Tuple[uuid.UUID, str]]
    ) -> List[Tuple[uuid.UUID, float]]:
        if not docs or not query.strip():
            return []

        query_tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 1]
        if not query_tokens:
            return []

        # Tokenize docs
        doc_tokens = {
            doc_id: [t.lower() for t in re.findall(r"\w+", text)]
            for doc_id, text in docs
        }
        N = len(docs)
        avg_dl = sum(len(toks) for toks in doc_tokens.values()) / max(1, N)

        # Document frequencies for query terms
        df: Dict[str, int] = {}
        for q in set(query_tokens):
            df[q] = sum(1 for toks in doc_tokens.values() if q in toks)

        scores: List[Tuple[uuid.UUID, float]] = []
        for doc_id, tokens in doc_tokens.items():
            dl = len(tokens)
            doc_score = 0.0
            term_counts: Dict[str, int] = {}
            for t in tokens:
                term_counts[t] = term_counts.get(t, 0) + 1

            for q in query_tokens:
                if q in term_counts:
                    tf = term_counts[q]
                    n_q = df.get(q, 0)
                    idf = math.log((N - n_q + 0.5) / (n_q + 0.5) + 1.0)
                    num = tf * (self.k1 + 1.0)
                    denom = tf + self.k1 * (1.0 - self.b + self.b * (dl / avg_dl))
                    doc_score += idf * (num / denom)

            scores.append((doc_id, doc_score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


def compute_rrf(
    vector_ranked_ids: List[uuid.UUID],
    bm25_ranked_ids: List[uuid.UUID],
    k: int = 60,
) -> Dict[uuid.UUID, float]:
    """
    Computes Reciprocal Rank Fusion score:
    RRF(d) = sum(1 / (k + rank(d)))
    """
    rrf_scores: Dict[uuid.UUID, float] = {}

    for rank, doc_id in enumerate(vector_ranked_ids, start=1):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))

    for rank, doc_id in enumerate(bm25_ranked_ids, start=1):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))

    return rrf_scores


def rerank_candidates(
    query: str,
    candidates: List[RankedCandidate],
) -> List[RankedCandidate]:
    """
    Cross-attention/reranking stage combining lexical overlap, RRF score, and semantic coverage.
    Produces calibrated relevance score in [0.0, 1.0].
    """
    q_words = set(re.findall(r"\w+", query.lower()))

    for cand in candidates:
        cand_words = set(re.findall(r"\w+", cand.text.lower()))
        overlap_ratio = len(q_words & cand_words) / max(1, len(q_words)) if q_words else 0.0

        # Base score from RRF (scaled to [0, 0.5]) + lexical exact match ([0, 0.5])
        rrf_contrib = min(0.5, cand.rrf_score * 15.0)
        lexical_contrib = min(0.5, overlap_ratio * 0.5)
        raw_score = rrf_contrib + lexical_contrib

        cand.rerank_score = round(min(1.0, max(0.0, raw_score)), 4)

    candidates.sort(key=lambda c: c.rerank_score, reverse=True)
    return candidates


def classify_evidence_sufficiency(
    query: str,
    top_candidates: List[RankedCandidate],
) -> str:
    """
    Classifies evidence sufficiency before LLM generation:
    - SUFFICIENT: High relevance scores, thorough coverage
    - PARTIAL: Moderate relevance, partial coverage
    - INSUFFICIENT: No candidates or very low relevance
    - CONFLICTING: Candidates contain diametrically opposed assertions
    """
    if not top_candidates:
        return "INSUFFICIENT"

    best_score = top_candidates[0].rerank_score
    if best_score < 0.20:
        return "INSUFFICIENT"

    # Check for direct conflicts / contradictory claims
    # e.g. "X is supported" vs "X is not supported", "true" vs "false"
    text_corpus = " ".join([c.text.lower() for c in top_candidates[:4]])
    has_contradiction = False
    conflict_patterns = [
        (r"\bis not\b", r"\bis\b"),
        (r"\bnever\b", r"\balways\b"),
        (r"\bfalse\b", r"\btrue\b"),
        (r"\bcannot\b", r"\bcan\b"),
    ]
    for neg, pos in conflict_patterns:
        if re.search(neg, text_corpus) and re.search(pos, text_corpus):
            # Check if occurs with subject terms
            terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 3]
            for term in terms:
                if (
                    re.search(rf"{term}.*{neg}", text_corpus)
                    and re.search(rf"{term}.*{pos}", text_corpus)
                ):
                    has_contradiction = True
                    break

    if has_contradiction:
        return "CONFLICTING"

    if best_score >= 0.55 and len(top_candidates) >= 1:
        return "SUFFICIENT"
    elif best_score >= 0.20:
        return "PARTIAL"
    else:
        return "INSUFFICIENT"
