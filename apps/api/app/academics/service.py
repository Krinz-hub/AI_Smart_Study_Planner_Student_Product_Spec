import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.academics.models import Subject, Topic, TopicRelationship, Exam
from app.academics.schemas import (
    SubjectCreate,
    SubjectUpdate,
    TopicCreate,
    TopicUpdate,
    TopicRelationshipCreate,
    ExamCreate,
    ExamUpdate,
)
from app.common.errors import NotFoundException, ForbiddenException, InvalidRequestException
from app.common.logging import get_logger

logger = get_logger("academics_service")


# --- Subjects ---

async def create_subject(db: AsyncSession, user_id: uuid.UUID, sub_in: SubjectCreate) -> Subject:
    subject = Subject(
        user_id=user_id,
        name=sub_in.name.strip(),
        code=sub_in.code.strip() if sub_in.code else None,
        color=sub_in.color,
    )
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return subject


async def list_subjects(db: AsyncSession, user_id: uuid.UUID) -> List[Subject]:
    stmt = select(Subject).where(Subject.user_id == user_id).order_by(Subject.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_subject(db: AsyncSession, user_id: uuid.UUID, subject_id: uuid.UUID) -> Subject:
    stmt = select(Subject).where(Subject.id == subject_id)
    result = await db.execute(stmt)
    subject = result.scalar_one_or_none()
    if not subject:
        raise NotFoundException("Subject not found")
    if subject.user_id != user_id:
        raise ForbiddenException("You do not have access to this subject")
    return subject


async def update_subject(
    db: AsyncSession, user_id: uuid.UUID, subject_id: uuid.UUID, sub_in: SubjectUpdate
) -> Subject:
    subject = await get_subject(db, user_id, subject_id)
    update_dict = sub_in.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if value is not None and isinstance(value, str):
            value = value.strip()
        setattr(subject, field, value)

    await db.commit()
    await db.refresh(subject)
    return subject


async def delete_subject(db: AsyncSession, user_id: uuid.UUID, subject_id: uuid.UUID) -> None:
    subject = await get_subject(db, user_id, subject_id)
    await db.delete(subject)
    await db.commit()


# --- Topics ---

async def create_topic(
    db: AsyncSession, user_id: uuid.UUID, subject_id: uuid.UUID, topic_in: TopicCreate
) -> Topic:
    # Verify subject ownership
    await get_subject(db, user_id, subject_id)

    if topic_in.parent_topic_id:
        parent = await db.get(Topic, topic_in.parent_topic_id)
        if not parent or parent.subject_id != subject_id:
            raise InvalidRequestException("Parent topic must belong to the same subject")

    topic = Topic(
        subject_id=subject_id,
        parent_topic_id=topic_in.parent_topic_id,
        name=topic_in.name.strip(),
        description=topic_in.description,
        syllabus_weight=topic_in.syllabus_weight,
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic


async def list_topics_by_subject(
    db: AsyncSession, user_id: uuid.UUID, subject_id: uuid.UUID
) -> List[Topic]:
    await get_subject(db, user_id, subject_id)
    stmt = select(Topic).where(Topic.subject_id == subject_id).order_by(Topic.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_topic_with_ownership(
    db: AsyncSession, user_id: uuid.UUID, topic_id: uuid.UUID
) -> Topic:
    stmt = (
        select(Topic)
        .options(joinedload(Topic.subject))
        .where(Topic.id == topic_id)
    )
    result = await db.execute(stmt)
    topic = result.scalar_one_or_none()
    if not topic:
        raise NotFoundException("Topic not found")
    if topic.subject.user_id != user_id:
        raise ForbiddenException("You do not have access to this topic")
    return topic


async def update_topic(
    db: AsyncSession, user_id: uuid.UUID, topic_id: uuid.UUID, topic_in: TopicUpdate
) -> Topic:
    topic = await get_topic_with_ownership(db, user_id, topic_id)

    if topic_in.parent_topic_id:
        if topic_in.parent_topic_id == topic_id:
            raise InvalidRequestException("A topic cannot be its own parent")
        parent = await db.get(Topic, topic_in.parent_topic_id)
        if not parent or parent.subject_id != topic.subject_id:
            raise InvalidRequestException("Parent topic must belong to the same subject")

    update_dict = topic_in.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(topic, field, value)

    await db.commit()
    await db.refresh(topic)
    return topic


# --- Topic Relationships ---

async def create_topic_relationship(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_topic_id: uuid.UUID,
    rel_in: TopicRelationshipCreate,
) -> TopicRelationship:
    if source_topic_id == rel_in.target_topic_id:
        raise InvalidRequestException("Cannot create a relationship from a topic to itself")

    source_topic = await get_topic_with_ownership(db, user_id, source_topic_id)
    target_topic = await get_topic_with_ownership(db, user_id, rel_in.target_topic_id)

    # Check for existing relationship
    stmt = select(TopicRelationship).where(
        TopicRelationship.source_topic_id == source_topic_id,
        TopicRelationship.target_topic_id == rel_in.target_topic_id,
        TopicRelationship.relationship_type == rel_in.relationship_type,
    )
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise InvalidRequestException("This topic relationship already exists")

    rel = TopicRelationship(
        source_topic_id=source_topic_id,
        target_topic_id=rel_in.target_topic_id,
        relationship_type=rel_in.relationship_type,
        confidence=rel_in.confidence,
        source=rel_in.source,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel


# --- Exams ---

async def create_exam(db: AsyncSession, user_id: uuid.UUID, exam_in: ExamCreate) -> Exam:
    await get_subject(db, user_id, exam_in.subject_id)
    exam = Exam(
        user_id=user_id,
        subject_id=exam_in.subject_id,
        name=exam_in.name.strip(),
        exam_at=exam_in.exam_at,
    )
    db.add(exam)
    await db.commit()
    await db.refresh(exam)
    return exam


async def list_exams(db: AsyncSession, user_id: uuid.UUID) -> List[Exam]:
    stmt = select(Exam).where(Exam.user_id == user_id).order_by(Exam.exam_at)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_exam(db: AsyncSession, user_id: uuid.UUID, exam_id: uuid.UUID) -> Exam:
    stmt = select(Exam).where(Exam.id == exam_id)
    result = await db.execute(stmt)
    exam = result.scalar_one_or_none()
    if not exam:
        raise NotFoundException("Exam not found")
    if exam.user_id != user_id:
        raise ForbiddenException("You do not have access to this exam")
    return exam


async def update_exam(
    db: AsyncSession, user_id: uuid.UUID, exam_id: uuid.UUID, exam_in: ExamUpdate
) -> Exam:
    exam = await get_exam(db, user_id, exam_id)
    update_dict = exam_in.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(exam, field, value)

    await db.commit()
    await db.refresh(exam)
    return exam


async def delete_exam(db: AsyncSession, user_id: uuid.UUID, exam_id: uuid.UUID) -> None:
    exam = await get_exam(db, user_id, exam_id)
    await db.delete(exam)
    await db.commit()
