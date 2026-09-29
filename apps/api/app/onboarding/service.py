import uuid
from decimal import Decimal
from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.mongo import get_mongo_db
from app.common.errors import InvalidRequestException, NotFoundException
from app.common.logging import get_logger
from app.academics.service import create_subject, create_topic
from app.academics.schemas import SubjectCreate, TopicCreate
from app.academics.models import Subject, Topic, Exam
from app.students.models import Goal, AvailabilityWindow
from app.quiz.models import Question
from app.quiz.generator import QuestionGenerator
from app.learner.models import MasteryState
from app.learner.intelligence_service import process_knowledge_observation
from app.planner.service import generate_study_plan
from app.planner.schemas import PlanGenerateRequest
from app.onboarding.discovery import discover_academic_syllabus
from app.onboarding.schemas import (
    AcademicTypeEnum,
    OnboardingStepEnum,
    SchoolProfileDetails,
    CollegeProfileDetails,
    CompetitiveExamProfileDetails,
    OtherProfileDetails,
    DiscoveredSyllabusResponse,
    ConfirmSyllabusRequest,
    ConfirmSyllabusResponse,
    SetupGoalsAndAvailabilityRequest,
    SetupGoalsAndAvailabilityResponse,
    DiagnosticGenerateResponse,
    DiagnosticQuestion,
    DiagnosticOption,
    DiagnosticSubmitRequest,
    DiagnosticSubmitResponse,
    TopicMasteryResult,
)

logger = get_logger("onboarding_service")


async def get_or_create_onboarding_record(user_id: uuid.UUID) -> Dict[str, Any]:
    """Retrieves or initializes user onboarding progress in MongoDB."""
    mongo_db = get_mongo_db()
    str_id = str(user_id)
    doc = await mongo_db.student_onboarding.find_one({"user_id": str_id})
    if not doc:
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": str_id,
            "current_step": OnboardingStepEnum.ACADEMIC_TYPE.value,
            "academic_type": None,
            "academic_details": {},
            "is_completed": False,
            "created_at": now,
            "updated_at": now,
        }
        await mongo_db.student_onboarding.insert_one(doc)
    return doc


def validate_profile_details(academic_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
    """Validates details payload against type-specific Pydantic schemas."""
    try:
        if academic_type == AcademicTypeEnum.SCHOOL.value:
            validated = SchoolProfileDetails(**details)
            return validated.model_dump()
        elif academic_type == AcademicTypeEnum.COLLEGE.value:
            validated = CollegeProfileDetails(**details)
            return validated.model_dump()
        elif academic_type == AcademicTypeEnum.COMPETITIVE_EXAM.value:
            validated = CompetitiveExamProfileDetails(**details)
            return validated.model_dump()
        else:
            validated = OtherProfileDetails(**details)
            return validated.model_dump()
    except Exception as e:
        logger.warning("profile_validation_failed", academic_type=academic_type, error=str(e))
        raise InvalidRequestException(f"Invalid {academic_type} academic profile details: {str(e)}")


async def set_academic_type(user_id: uuid.UUID, academic_type: AcademicTypeEnum) -> Dict[str, Any]:
    """Sets student academic category and advances state to ACADEMIC_PROFILE."""
    mongo_db = get_mongo_db()
    str_id = str(user_id)
    now = datetime.now(timezone.utc)

    result = await mongo_db.student_onboarding.find_one_and_update(
        {"user_id": str_id},
        {
            "$set": {
                "academic_type": academic_type.value,
                "current_step": OnboardingStepEnum.ACADEMIC_PROFILE.value,
                "updated_at": now,
            }
        },
        upsert=True,
        return_document=True,
    )
    logger.info("academic_type_selected", user_id=str_id, academic_type=academic_type.value)
    return result or await get_or_create_onboarding_record(user_id)


async def set_academic_profile(user_id: uuid.UUID, raw_details: Dict[str, Any]) -> Dict[str, Any]:
    """Saves detailed institution/program info and advances step to ACADEMIC_DISCOVERY."""
    mongo_db = get_mongo_db()
    str_id = str(user_id)
    current = await get_or_create_onboarding_record(user_id)

    academic_type = current.get("academic_type") or AcademicTypeEnum.COLLEGE.value
    validated_details = validate_profile_details(academic_type, raw_details)

    now = datetime.now(timezone.utc)
    result = await mongo_db.student_onboarding.find_one_and_update(
        {"user_id": str_id},
        {
            "$set": {
                "academic_details": validated_details,
                "current_step": OnboardingStepEnum.ACADEMIC_DISCOVERY.value,
                "updated_at": now,
            }
        },
        return_document=True,
    )
    logger.info("academic_profile_saved", user_id=str_id, academic_type=academic_type)
    return result or await get_or_create_onboarding_record(user_id)


async def advance_onboarding_step(user_id: uuid.UUID, next_step: OnboardingStepEnum) -> Dict[str, Any]:
    """Advances student onboarding state machine to specified step."""
    mongo_db = get_mongo_db()
    str_id = str(user_id)
    now = datetime.now(timezone.utc)

    is_complete = (next_step == OnboardingStepEnum.COMPLETED)
    update_fields: Dict[str, Any] = {
        "current_step": next_step.value,
        "is_completed": is_complete,
        "updated_at": now,
    }
    if is_complete:
        update_fields["completed_at"] = now

    result = await mongo_db.student_onboarding.find_one_and_update(
        {"user_id": str_id},
        {"$set": update_fields},
        return_document=True,
    )
    logger.info("onboarding_step_advanced", user_id=str_id, next_step=next_step.value)
    return result or await get_or_create_onboarding_record(user_id)


async def trigger_academic_discovery(user_id: uuid.UUID) -> DiscoveredSyllabusResponse:
    """Executes discovery engine on student profile and saves candidates to MongoDB."""
    record = await get_or_create_onboarding_record(user_id)
    academic_type = record.get("academic_type") or AcademicTypeEnum.COLLEGE.value
    academic_details = record.get("academic_details", {})

    discovery_result = await discover_academic_syllabus(academic_type, academic_details)

    mongo_db = get_mongo_db()
    str_id = str(user_id)
    now = datetime.now(timezone.utc)

    await mongo_db.student_onboarding.update_one(
        {"user_id": str_id},
        {
            "$set": {
                "discovered_syllabus": discovery_result.model_dump(),
                "current_step": OnboardingStepEnum.SYLLABUS_REVIEW.value,
                "updated_at": now,
            }
        },
    )
    logger.info("academic_discovery_completed", user_id=str_id, subjects_count=len(discovery_result.subjects))
    return discovery_result


async def confirm_and_persist_syllabus(
    db: AsyncSession,
    user_id: uuid.UUID,
    req: ConfirmSyllabusRequest,
) -> ConfirmSyllabusResponse:
    """
    Persists reviewed/customized syllabus into authoritative PostgreSQL relational tables:
    - Creates Subject records
    - Creates Topic records for each unit/topic
    - Updates MongoDB onboarding state to GOALS_EXAMS
    """
    subjects_created = 0
    topics_created = 0

    for sub_item in req.subjects:
        # Create subject in PostgreSQL
        sub_create = SubjectCreate(
            name=sub_item.name,
            code=sub_item.code,
            color=sub_item.color_code or "#3b82f6",
        )
        pg_sub = await create_subject(db, user_id, sub_create)
        subjects_created += 1

        # Create topics under subject in PostgreSQL
        for t_name in sub_item.topics:
            t_create = TopicCreate(name=t_name)
            await create_topic(db, user_id, pg_sub.id, t_create)
            topics_created += 1

    # Advance state machine to GOALS_EXAMS in MongoDB
    mongo_db = get_mongo_db()
    str_id = str(user_id)
    now = datetime.now(timezone.utc)

    await mongo_db.student_onboarding.update_one(
        {"user_id": str_id},
        {
            "$set": {
                "current_step": OnboardingStepEnum.GOALS_EXAMS.value,
                "updated_at": now,
            }
        },
    )
    logger.info(
        "syllabus_confirmed_and_persisted",
        user_id=str_id,
        subjects=subjects_created,
        topics=topics_created,
    )
    return ConfirmSyllabusResponse(
        status="success",
        subjects_created=subjects_created,
        topics_created=topics_created,
        current_step=OnboardingStepEnum.GOALS_EXAMS.value,
    )


async def setup_goals_and_availability(
    db: AsyncSession,
    user_id: uuid.UUID,
    req: SetupGoalsAndAvailabilityRequest,
) -> SetupGoalsAndAvailabilityResponse:
    """
    Saves student study goals, exams, and weekly availability into PostgreSQL,
    stores preferences in MongoDB, and advances onboarding step to DIAGNOSTIC.
    """
    exams_created = 0
    goals_created = 0
    slots_created = 0

    # 1. Create Exams in PostgreSQL
    if req.exams:
        # Fetch user's subjects if needed for default linking
        subj_stmt = select(Subject).where(Subject.user_id == user_id).limit(1)
        subj_res = await db.execute(subj_stmt)
        default_subj = subj_res.scalar_one_or_none()

        for ex in req.exams:
            sub_id = ex.subject_id or (default_subj.id if default_subj else None)
            if sub_id:
                exam_obj = Exam(
                    user_id=user_id,
                    subject_id=sub_id,
                    name=ex.name,
                    exam_at=ex.exam_at,
                )
                db.add(exam_obj)
                exams_created += 1

    # 2. Create Goals in PostgreSQL
    if req.goals:
        for g in req.goals:
            goal_obj = Goal(
                user_id=user_id,
                subject_id=g.subject_id,
                title=g.title,
                target_type=g.target_type,
                target_value=Decimal(str(g.target_value)) if g.target_value is not None else None,
                deadline=g.deadline,
                priority=Decimal(str(g.priority)),
                status="active",
            )
            db.add(goal_obj)
            goals_created += 1

    # 3. Create AvailabilityWindows in PostgreSQL
    if req.weekly_availability:
        # Clear existing availability to prevent duplicates
        await db.execute(delete(AvailabilityWindow).where(AvailabilityWindow.user_id == user_id))
        for slot in req.weekly_availability:
            s_parts = [int(p) for p in slot.start_time.split(":")[:2]]
            e_parts = [int(p) for p in slot.end_time.split(":")[:2]]
            win = AvailabilityWindow(
                user_id=user_id,
                weekday=slot.weekday,
                start_time=time(hour=s_parts[0], minute=s_parts[1]),
                end_time=time(hour=e_parts[0], minute=e_parts[1]),
                enabled=slot.enabled,
            )
            db.add(win)
            slots_created += 1

    await db.commit()

    # 4. Save preferences in MongoDB and advance onboarding step
    mongo_db = get_mongo_db()
    str_id = str(user_id)
    now = datetime.now(timezone.utc)

    await mongo_db.student_preferences.update_one(
        {"user_id": str_id},
        {
            "$set": {
                "user_id": str_id,
                "daily_capacity_minutes": req.daily_capacity_minutes,
                "study_time_preference": req.study_time_preference,
                "weekly_availability": [s.model_dump() for s in req.weekly_availability],
                "updated_at": now,
            }
        },
        upsert=True,
    )

    await mongo_db.student_onboarding.update_one(
        {"user_id": str_id},
        {
            "$set": {
                "current_step": OnboardingStepEnum.DIAGNOSTIC.value,
                "updated_at": now,
            }
        },
    )

    logger.info(
        "goals_and_availability_configured",
        user_id=str_id,
        exams=exams_created,
        goals=goals_created,
        slots=slots_created,
    )

    return SetupGoalsAndAvailabilityResponse(
        status="success",
        exams_created=exams_created,
        goals_created=goals_created,
        availability_slots_created=slots_created,
        daily_capacity_minutes=req.daily_capacity_minutes,
        current_step=OnboardingStepEnum.DIAGNOSTIC.value,
    )


async def generate_diagnostic_test(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> DiagnosticGenerateResponse:
    """
    Generates a personalized diagnostic baseline test across student's confirmed syllabus.
    Correct answers are concealed from the returned student view.
    """
    # 1. Fetch confirmed topics and their parent subjects
    stmt = (
        select(Topic, Subject)
        .join(Subject, Subject.id == Topic.subject_id)
        .where(Subject.user_id == user_id)
        .order_by(Subject.created_at.asc(), Topic.created_at.asc())
        .limit(10)
    )
    res = await db.execute(stmt)
    topic_rows = res.all()

    if not topic_rows:
        return DiagnosticGenerateResponse(
            status="success",
            total_questions=0,
            questions=[],
        )

    # 2. Generate candidate question for each topic
    created_questions: List[DiagnosticQuestion] = []
    for topic, subject in topic_rows:
        candidates = QuestionGenerator.generate_candidate_questions(
            topic_name=topic.name,
            topic_id=topic.id,
            num_questions=1,
            difficulty="MEDIUM",
        )
        if candidates:
            c = candidates[0]
            q = Question(
                topic_id=topic.id,
                question_type=c["question_type"],
                difficulty=c["difficulty"],
                predicted_difficulty=c.get("predicted_difficulty"),
                question_text=c["question_text"],
                options=c["options"],
                correct_answer=c["correct_answer"],
                explanation=c["explanation"],
                source_id=c.get("source_id"),
                source_chunk_id=c.get("source_chunk_id"),
                generation_model=c.get("generation_model", "diagnostic-generator-v1"),
                generation_version=c.get("generation_version", "v1"),
            )
            db.add(q)
            await db.commit()
            await db.refresh(q)

            opts = [DiagnosticOption(key=o["key"], text=o["text"]) for o in (q.options or [])]
            created_questions.append(
                DiagnosticQuestion(
                    id=q.id,
                    topic_id=topic.id,
                    topic_name=topic.name,
                    subject_name=subject.name,
                    question_text=q.question_text,
                    difficulty=q.difficulty,
                    options=opts,
                )
            )

    logger.info("diagnostic_test_generated", user_id=str(user_id), count=len(created_questions))
    return DiagnosticGenerateResponse(
        status="success",
        total_questions=len(created_questions),
        questions=created_questions,
    )


async def submit_diagnostic_test(
    db: AsyncSession,
    user_id: uuid.UUID,
    req: DiagnosticSubmitRequest,
) -> DiagnosticSubmitResponse:
    """
    Evaluates diagnostic responses, updates BKT mastery states,
    produces the student's initial study plan via OR-Tools, and completes onboarding.
    """
    total_answered = len(req.answers)
    correct_count = 0
    evaluated_topic_ids = set()

    for item in req.answers:
        q_stmt = select(Question).where(Question.id == item.question_id)
        q_res = await db.execute(q_stmt)
        question = q_res.scalar_one_or_none()
        if not question:
            continue

        # Extract correct key
        correct_key = ""
        if isinstance(question.correct_answer, dict):
            correct_key = question.correct_answer.get("key", "")
        elif isinstance(question.correct_answer, str):
            correct_key = question.correct_answer

        is_corr = (item.selected_key.strip().upper() == correct_key.strip().upper())
        if is_corr:
            correct_count += 1

        evaluated_topic_ids.add(question.topic_id)

        # Update BKT knowledge observation in PostgreSQL
        await process_knowledge_observation(
            db=db,
            user_id=user_id,
            topic_id=question.topic_id,
            is_correct=is_corr,
            response_time_seconds=item.response_time_seconds or 10,
        )

    accuracy_pct = round((correct_count / total_answered * 100.0), 1) if total_answered > 0 else 0.0

    # Retrieve updated mastery states
    topic_masteries: List[TopicMasteryResult] = []
    for tid in evaluated_topic_ids:
        t_stmt = (
            select(Topic, MasteryState)
            .join(MasteryState, MasteryState.topic_id == Topic.id)
            .where(Topic.id == tid, MasteryState.user_id == user_id)
        )
        t_res = await db.execute(t_stmt)
        row = t_res.first()
        if row:
            top, mstate = row
            topic_masteries.append(
                TopicMasteryResult(
                    topic_id=top.id,
                    topic_name=top.name,
                    mastery_probability=float(mstate.mastery_probability),
                    state=mstate.state,
                )
            )

    # Produce the First Initial Study Plan
    mongo_db = get_mongo_db()
    str_id = str(user_id)
    pref = await mongo_db.student_preferences.find_one({"user_id": str_id})
    daily_cap = pref.get("daily_capacity_minutes", 180) if pref else 180

    plan_req = PlanGenerateRequest(
        daily_capacity_minutes=daily_cap,
        preserve_locked_tasks=True,
    )
    plan_res = await generate_study_plan(db, user_id, plan_req)
    tasks_scheduled = len(plan_res.tasks)

    # Advance Onboarding to COMPLETED in MongoDB
    now = datetime.now(timezone.utc)
    await mongo_db.student_onboarding.update_one(
        {"user_id": str_id},
        {
            "$set": {
                "current_step": OnboardingStepEnum.COMPLETED.value,
                "is_completed": True,
                "completed_at": now,
                "diagnostic_accuracy_pct": accuracy_pct,
                "initial_tasks_count": tasks_scheduled,
                "updated_at": now,
            }
        },
    )

    logger.info(
        "diagnostic_completed_and_plan_created",
        user_id=str_id,
        accuracy=accuracy_pct,
        tasks_scheduled=tasks_scheduled,
    )

    return DiagnosticSubmitResponse(
        status="success",
        total_answered=total_answered,
        correct_count=correct_count,
        accuracy_pct=accuracy_pct,
        topic_masteries=topic_masteries,
        plan_tasks_scheduled=tasks_scheduled,
        current_step=OnboardingStepEnum.COMPLETED.value,
        is_completed=True,
    )

