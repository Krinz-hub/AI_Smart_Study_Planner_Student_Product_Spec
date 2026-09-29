import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.academics.schemas import (
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
    TopicCreate,
    TopicUpdate,
    TopicResponse,
    TopicRelationshipCreate,
    TopicRelationshipResponse,
    ExamCreate,
    ExamUpdate,
    ExamResponse,
)
from app.academics.service import (
    create_subject,
    list_subjects,
    get_subject,
    update_subject,
    delete_subject,
    create_topic,
    list_topics_by_subject,
    get_topic_with_ownership,
    update_topic,
    create_topic_relationship,
    create_exam,
    list_exams,
    get_exam,
    update_exam,
    delete_exam,
)

router = APIRouter(tags=["academics"])


# --- Subjects ---

@router.get("/subjects", response_model=List[SubjectResponse])
async def get_subjects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[SubjectResponse]:
    subjects = await list_subjects(db, current_user.id)
    return [SubjectResponse.model_validate(s) for s in subjects]


@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def post_subject(
    req: SubjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubjectResponse:
    subject = await create_subject(db, current_user.id, req)
    return SubjectResponse.model_validate(subject)


@router.patch("/subjects/{subject_id}", response_model=SubjectResponse)
async def patch_subject(
    subject_id: uuid.UUID,
    req: SubjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubjectResponse:
    subject = await update_subject(db, current_user.id, subject_id, req)
    return SubjectResponse.model_validate(subject)


@router.delete("/subjects/{subject_id}")
async def remove_subject(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    await delete_subject(db, current_user.id, subject_id)
    return {"status": "success", "message": "Subject deleted"}


# --- Topics ---

@router.get("/subjects/{subject_id}/topics", response_model=List[TopicResponse])
async def get_topics(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[TopicResponse]:
    topics = await list_topics_by_subject(db, current_user.id, subject_id)
    return [TopicResponse.model_validate(t) for t in topics]


@router.post("/subjects/{subject_id}/topics", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
async def post_topic(
    subject_id: uuid.UUID,
    req: TopicCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicResponse:
    topic = await create_topic(db, current_user.id, subject_id, req)
    return TopicResponse.model_validate(topic)


@router.get("/subjects/{subject_id}/topics/{topic_id}", response_model=TopicResponse)
async def get_subject_topic(
    subject_id: uuid.UUID,
    topic_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicResponse:
    topic = await get_topic_with_ownership(db, current_user.id, topic_id)
    return TopicResponse.model_validate(topic)


@router.get("/topics/{topic_id}", response_model=TopicResponse)
async def get_topic_by_id(
    topic_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicResponse:
    topic = await get_topic_with_ownership(db, current_user.id, topic_id)
    return TopicResponse.model_validate(topic)


@router.patch("/topics/{topic_id}", response_model=TopicResponse)
async def patch_topic(
    topic_id: uuid.UUID,
    req: TopicUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicResponse:
    topic = await update_topic(db, current_user.id, topic_id, req)
    return TopicResponse.model_validate(topic)


@router.post("/topics/{topic_id}/relationships", response_model=TopicRelationshipResponse, status_code=status.HTTP_201_CREATED)
async def post_topic_relationship(
    topic_id: uuid.UUID,
    req: TopicRelationshipCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicRelationshipResponse:
    rel = await create_topic_relationship(db, current_user.id, topic_id, req)
    return TopicRelationshipResponse.model_validate(rel)


# --- Exams ---

@router.get("/exams", response_model=List[ExamResponse])
async def get_exams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ExamResponse]:
    exams = await list_exams(db, current_user.id)
    return [ExamResponse.model_validate(e) for e in exams]


@router.post("/exams", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def post_exam(
    req: ExamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamResponse:
    exam = await create_exam(db, current_user.id, req)
    return ExamResponse.model_validate(exam)


@router.patch("/exams/{exam_id}", response_model=ExamResponse)
async def patch_exam(
    exam_id: uuid.UUID,
    req: ExamUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExamResponse:
    exam = await update_exam(db, current_user.id, exam_id, req)
    return ExamResponse.model_validate(exam)


@router.delete("/exams/{exam_id}")
async def remove_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    await delete_exam(db, current_user.id, exam_id)
    return {"status": "success", "message": "Exam deleted"}
