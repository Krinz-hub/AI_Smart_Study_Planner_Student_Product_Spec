import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.learner.models import LearnerEvent, AuditLog
from app.learner.schemas import (
    LearnerEventCreate,
    LearnerEventResponse,
    LearnerFeedbackRequest,
    TopicEvidenceResponse,
)
from app.common.logging import get_logger

logger = get_logger("event_service")


async def record_event(
    db: AsyncSession, user_id: uuid.UUID, event_in: LearnerEventCreate
) -> LearnerEvent:
    """Records an append-only learner event with idempotency guarantees."""
    if event_in.idempotency_key:
        stmt = select(LearnerEvent).where(
            LearnerEvent.idempotency_key == event_in.idempotency_key,
            LearnerEvent.user_id == user_id,
        )
        existing = await db.execute(stmt)
        record = existing.scalar_one_or_none()
        if record:
            logger.info("idempotent_event_deduplicated", idempotency_key=event_in.idempotency_key)
            return record

    event = LearnerEvent(
        user_id=user_id,
        event_type=event_in.event_type,
        entity_type=event_in.entity_type,
        entity_id=event_in.entity_id,
        evidence_category=event_in.evidence_category,
        idempotency_key=event_in.idempotency_key,
        payload=event_in.payload,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    logger.info(
        "learner_event_recorded",
        user_id=str(user_id),
        event_type=event.event_type,
        category=event.evidence_category,
    )
    return event


async def record_audit(
    db: AsyncSession,
    action: str,
    entity_type: str,
    user_id: Optional[uuid.UUID] = None,
    actor_type: str = "student",
    entity_id: Optional[uuid.UUID] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Records an immutable audit trail entry."""
    audit = AuditLog(
        user_id=user_id,
        actor_type=actor_type,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata_json or {},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)
    return audit


async def submit_feedback(
    db: AsyncSession, user_id: uuid.UUID, feedback_in: LearnerFeedbackRequest
) -> LearnerEvent:
    """Records student feedback on recommendations or learning content."""
    payload = {
        "feedback_type": feedback_in.feedback_type,
        "notes": feedback_in.notes,
        "topic_id": str(feedback_in.topic_id) if feedback_in.topic_id else None,
        "task_id": str(feedback_in.task_id) if feedback_in.task_id else None,
    }

    event_in = LearnerEventCreate(
        event_type="RECOMMENDATION_FEEDBACK",
        entity_type="topic" if feedback_in.topic_id else "task",
        entity_id=feedback_in.topic_id or feedback_in.task_id,
        evidence_category="SELF_REPORT",
        payload=payload,
    )

    event = await record_event(db, user_id, event_in)

    # Record audit log
    await record_audit(
        db,
        action="SUBMIT_FEEDBACK",
        entity_type="feedback",
        user_id=user_id,
        entity_id=event.id,
        metadata_json={"feedback_type": feedback_in.feedback_type},
    )

    return event


async def get_topic_evidence(
    db: AsyncSession, user_id: uuid.UUID, topic_id: uuid.UUID
) -> TopicEvidenceResponse:
    """Retrieves and classifies all recorded evidence for a given topic."""
    # Find events where entity_id is topic_id or payload contains topic_id
    topic_id_str = str(topic_id)
    stmt = (
        select(LearnerEvent)
        .where(
            LearnerEvent.user_id == user_id,
            or_(
                LearnerEvent.entity_id == topic_id,
                LearnerEvent.payload["topic_id"].as_string() == topic_id_str,
            ),
        )
        .order_by(LearnerEvent.created_at.desc())
    )
    result = await db.execute(stmt)
    events = list(result.scalars().all())

    knowledge_ev: List[LearnerEventResponse] = []
    behavior_ev: List[LearnerEventResponse] = []
    self_report_ev: List[LearnerEventResponse] = []

    for ev in events:
        resp = LearnerEventResponse.model_validate(ev)
        if ev.evidence_category == "KNOWLEDGE":
            knowledge_ev.append(resp)
        elif ev.evidence_category == "SELF_REPORT":
            self_report_ev.append(resp)
        else:
            behavior_ev.append(resp)

    return TopicEvidenceResponse(
        topic_id=topic_id,
        knowledge_evidence=knowledge_ev,
        behavior_evidence=behavior_ev,
        self_report_evidence=self_report_ev,
        total_evidence_count=len(events),
    )


async def list_recent_events(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 50
) -> List[LearnerEvent]:
    stmt = (
        select(LearnerEvent)
        .where(LearnerEvent.user_id == user_id)
        .order_by(LearnerEvent.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
