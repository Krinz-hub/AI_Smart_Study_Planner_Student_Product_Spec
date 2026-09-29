from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.tutor.schemas import TutorChatRequest, TutorChatResponse
from app.tutor.service import generate_tutor_response

router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.post("/chat", response_model=TutorChatResponse)
async def post_tutor_chat(
    req: TutorChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TutorChatResponse:
    """Grounded AI tutor supporting Socratic, ELI5, Deep Dive, Hint, and Exam Answer modes with source citations."""
    return await generate_tutor_response(db, current_user.id, req)
