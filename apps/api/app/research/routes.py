from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.research.schemas import (
    WebSearchRequest,
    WebSearchResponse,
    SafeFetchRequest,
    SafeFetchResponse,
)
from app.research.service import perform_web_search, perform_safe_fetch

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/search", response_model=WebSearchResponse)
async def post_search(
    req: WebSearchRequest,
    current_user: User = Depends(get_current_user),
) -> WebSearchResponse:
    """Executes optional web search for supplementary academic material with caching."""
    return await perform_web_search(req)


@router.post("/fetch", response_model=SafeFetchResponse)
async def post_fetch(
    req: SafeFetchRequest,
    current_user: User = Depends(get_current_user),
) -> SafeFetchResponse:
    """Performs SSRF-validated safe HTTP fetch of educational web resources."""
    return await perform_safe_fetch(req)
