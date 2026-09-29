import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.exam_mode.schemas import (
    ExamModeGenerateRequest,
    ExamPlanResponse,
    ExamPlanActionRequest,
)
from app.exam_mode.service import (
    generate_exam_mode_plan,
    get_exam_plan_by_id,
    handle_exam_plan_action,
)

router = APIRouter(prefix="/exam-mode", tags=["exam-mode"])


@router.post("/generate", response_model=ExamPlanResponse, status_code=status.HTTP_201_CREATED)
async def post_generate_exam_mode(
    req: ExamModeGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamPlanResponse:
    """Generates intensive exam preparation schedule with 100% syllabus coverage and rescue recovery."""
    return await generate_exam_mode_plan(db, current_user.id, req)


@router.get("/{plan_id}", response_model=ExamPlanResponse)
async def get_exam_mode_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamPlanResponse:
    """Retrieves generated exam preparation plan."""
    return await get_exam_plan_by_id(db, current_user.id, plan_id)


@router.post("/{plan_id}/action", response_model=ExamPlanResponse)
async def post_exam_mode_action(
    plan_id: uuid.UUID,
    req: ExamPlanActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamPlanResponse:
    """Accepts, customizes, or dismisses proposed exam plan."""
    return await handle_exam_plan_action(db, current_user.id, plan_id, req)
