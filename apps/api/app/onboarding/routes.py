import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.onboarding.schemas import (
    SelectAcademicTypeRequest,
    AcademicProfileRequest,
    OnboardingStatusResponse,
    DiscoveredSyllabusResponse,
    ConfirmSyllabusRequest,
    ConfirmSyllabusResponse,
    SetupGoalsAndAvailabilityRequest,
    SetupGoalsAndAvailabilityResponse,
    DiagnosticGenerateResponse,
    DiagnosticSubmitRequest,
    DiagnosticSubmitResponse,
)
from app.onboarding.service import (
    get_or_create_onboarding_record,
    set_academic_type,
    set_academic_profile,
    trigger_academic_discovery,
    confirm_and_persist_syllabus,
    setup_goals_and_availability,
    generate_diagnostic_test,
    submit_diagnostic_test,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_status(
    current_user: User = Depends(get_current_user),
) -> OnboardingStatusResponse:
    """Retrieves current student onboarding wizard progress and profile."""
    record = await get_or_create_onboarding_record(current_user.id)
    return OnboardingStatusResponse(
        user_id=current_user.id,
        current_step=record.get("current_step", "ACADEMIC_TYPE"),
        academic_type=record.get("academic_type"),
        academic_details=record.get("academic_details", {}),
        discovered_syllabus=record.get("discovered_syllabus"),
        is_completed=record.get("is_completed", False),
        updated_at=record.get("updated_at"),
    )


@router.post("/academic-type", response_model=OnboardingStatusResponse)
async def post_academic_type(
    req: SelectAcademicTypeRequest,
    current_user: User = Depends(get_current_user),
) -> OnboardingStatusResponse:
    """Selects educational track (School, College, Competitive Exam, Other) and advances state."""
    record = await set_academic_type(current_user.id, req.academic_type)
    return OnboardingStatusResponse(
        user_id=current_user.id,
        current_step=record.get("current_step", "ACADEMIC_PROFILE"),
        academic_type=record.get("academic_type"),
        academic_details=record.get("academic_details", {}),
        is_completed=record.get("is_completed", False),
        updated_at=record.get("updated_at"),
    )


@router.post("/academic-profile", response_model=OnboardingStatusResponse)
async def post_academic_profile(
    req: AcademicProfileRequest,
    current_user: User = Depends(get_current_user),
) -> OnboardingStatusResponse:
    """Saves detailed institution/program info and advances to syllabus discovery step."""
    record = await set_academic_profile(current_user.id, req.details)
    return OnboardingStatusResponse(
        user_id=current_user.id,
        current_step=record.get("current_step", "ACADEMIC_DISCOVERY"),
        academic_type=record.get("academic_type"),
        academic_details=record.get("academic_details", {}),
        is_completed=record.get("is_completed", False),
        updated_at=record.get("updated_at"),
    )


@router.post("/discover-syllabus", response_model=DiscoveredSyllabusResponse)
async def post_discover_syllabus(
    current_user: User = Depends(get_current_user),
) -> DiscoveredSyllabusResponse:
    """Discovers official syllabus and structure based on student academic profile."""
    return await trigger_academic_discovery(current_user.id)


@router.post("/confirm-syllabus", response_model=ConfirmSyllabusResponse)
async def post_confirm_syllabus(
    req: ConfirmSyllabusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConfirmSyllabusResponse:
    """Persists confirmed syllabus subjects and topics into relational PostgreSQL database."""
    return await confirm_and_persist_syllabus(db, current_user.id, req)


@router.post("/goals-availability", response_model=SetupGoalsAndAvailabilityResponse)
async def post_goals_availability(
    req: SetupGoalsAndAvailabilityRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SetupGoalsAndAvailabilityResponse:
    """Configures student target exams, mastery goals, daily capacity, and weekly availability."""
    return await setup_goals_and_availability(db, current_user.id, req)


@router.get("/diagnostic/generate", response_model=DiagnosticGenerateResponse)
@router.post("/diagnostic/generate", response_model=DiagnosticGenerateResponse)
async def get_or_generate_diagnostic(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiagnosticGenerateResponse:
    """Generates baseline diagnostic questions across confirmed syllabus with concealed answers."""
    return await generate_diagnostic_test(db, current_user.id)


@router.post("/diagnostic/submit", response_model=DiagnosticSubmitResponse)
async def post_submit_diagnostic(
    req: DiagnosticSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiagnosticSubmitResponse:
    """Submits diagnostic responses, initializes BKT mastery states, produces first study plan, and completes onboarding."""
    return await submit_diagnostic_test(db, current_user.id, req)

