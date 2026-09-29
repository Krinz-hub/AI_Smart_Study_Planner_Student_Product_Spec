import uuid
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.decisions.schemas import CandidateDecisionsResponse, Recommendation
from app.decisions.service import generate_recommendations

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("/recommendations", response_model=CandidateDecisionsResponse)
async def get_recommendations(
    subject_id: Optional[uuid.UUID] = None,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateDecisionsResponse:
    """Answers: What is worth doing next? Returns prioritized candidates with explainable reasons."""
    return await generate_recommendations(db, current_user.id, subject_id, limit)


@router.get("/next", response_model=Optional[Recommendation])
async def get_next_intervention(
    subject_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[Recommendation]:
    """Returns the single highest priority academic action."""
    response = await generate_recommendations(db, current_user.id, subject_id, limit=1)
    return response.top_recommendation
