import time
from typing import Dict, List, Tuple
import httpx

from app.research.provider import get_search_provider, SearchResult
from app.research.ssrf import validate_safe_url
from app.research.schemas import (
    WebSearchRequest,
    WebSearchResponse,
    WebSearchResultItem,
    SafeFetchRequest,
    SafeFetchResponse,
)
from app.common.errors import InvalidRequestException
from app.common.logging import get_logger

logger = get_logger("research_service")

# In-memory search cache: query -> (timestamp, List[SearchResult])
_cache: Dict[str, Tuple[float, List[SearchResult]]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


async def perform_web_search(req: WebSearchRequest) -> WebSearchResponse:
    query = req.query.strip().lower()
    now = time.time()

    # Check cache
    if query in _cache:
        cached_time, cached_results = _cache[query]
        if now - cached_time < CACHE_TTL_SECONDS:
            return WebSearchResponse(
                query=req.query,
                results=[
                    WebSearchResultItem(
                        title=r.title,
                        url=r.url,
                        snippet=r.snippet,
                        source=r.source,
                    )
                    for r in cached_results[:req.limit]
                ],
                provider="cache",
            )

    provider = get_search_provider()
    results = await provider.search(req.query, limit=req.limit)
    _cache[query] = (now, results)

    return WebSearchResponse(
        query=req.query,
        results=[
            WebSearchResultItem(
                title=r.title,
                url=r.url,
                snippet=r.snippet,
                source=r.source,
            )
            for r in results
        ],
        provider=provider.__class__.__name__,
    )


async def perform_safe_fetch(req: SafeFetchRequest) -> SafeFetchResponse:
    # 1. Strict SSRF Validation
    safe_url = validate_safe_url(req.url)

    # 2. Safe HTTP GET with strict timeout and payload size cap
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            res = await client.get(safe_url, headers={"User-Agent": "AISmartStudyPlanner/1.0"})
            if res.status_code >= 400:
                return SafeFetchResponse(
                    url=safe_url,
                    status=f"HTTP_{res.status_code}",
                    content_snippet="Unable to fetch page content.",
                )

            # Cap payload at 200KB to prevent memory exhaustion
            text = res.text[:200000]
            clean_snippet = text[:400].strip()
            return SafeFetchResponse(
                url=safe_url,
                status="SUCCESS",
                content_snippet=clean_snippet,
            )
    except Exception as e:
        logger.warning("safe_fetch_error", url=safe_url, error=str(e))
        return SafeFetchResponse(
            url=safe_url,
            status="ERROR",
            content_snippet=f"Failed to fetch: {str(e)}",
        )
