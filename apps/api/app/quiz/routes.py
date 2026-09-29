import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.quiz.schemas import (
    QuizGenerateRequest,
    QuizResponse,
    QuizSubmitRequest,
    QuizResultResponse,
)
from app.quiz.service import (
    create_quiz,
    start_quiz,
    evaluate_and_submit_quiz,
    get_quiz_results,
)

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.post("/generate", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def post_generate_quiz(
    req: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizResponse:
    """Generates schema-validated quiz questions aligned with learning objectives and course materials."""
    return await create_quiz(db, current_user.id, req)


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizResponse:
    """Retrieves quiz questions and metadata."""
    return await start_quiz(db, current_user.id, quiz_id)


@router.post("/{quiz_id}/start", response_model=QuizResponse)
async def post_start_quiz(
    quiz_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizResponse:
    """Marks quiz status as IN_PROGRESS."""
    return await start_quiz(db, current_user.id, quiz_id)


@router.post("/{quiz_id}/submit", response_model=QuizResultResponse)
async def post_submit_quiz(
    quiz_id: uuid.UUID,
    req: QuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizResultResponse:
    """Evaluates quiz submission, recalibrates question difficulties, and updates BKT/FSRS mastery state."""
    return await evaluate_and_submit_quiz(db, current_user.id, quiz_id, req)


@router.get("/{quiz_id}/results", response_model=QuizResultResponse)
async def get_results(
    quiz_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizResultResponse:
    """Retrieves detailed results, weak concepts, and explanations for a completed quiz."""
    return await get_quiz_results(db, current_user.id, quiz_id)
