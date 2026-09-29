from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.rag.schemas import RetrievalSearchRequest, RetrievalSearchResponse
from app.rag.service import search_and_rank

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalSearchResponse)
async def search_retrieval(
    req: RetrievalSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RetrievalSearchResponse:
    """Executes tenant-isolated hybrid retrieval with BM25, pgvector, RRF, and citation generation."""
    return await search_and_rank(db, current_user.id, req)
