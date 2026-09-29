import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learner.models import MasteryState, MemoryState, ConfidenceState, LearnerEvent
from app.learner.bkt import compute_bkt_posterior, compute_confidence, classify_mastery_state
from app.learner.fsrs import update_fsrs_state, compute_retrievability
from app.learner.calibration import evaluate_confidence_calibration
from app.learner.prerequisites import find_prerequisite_blockers
from app.learner.gaps import detect_knowledge_gaps
from app.learner.event_service import record_event, record_audit
from app.common.logging import get_logger

logger = get_logger("learner_intelligence")


async def get_or_create_mastery_state(
    db: AsyncSession, user_id: uuid.UUID, topic_id: uuid.UUID
) -> MasteryState:
    stmt = select(MasteryState).where(
        MasteryState.user_id == user_id,
        MasteryState.topic_id == topic_id,
    )
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()
    if not state:
        state = MasteryState(
            user_id=user_id,
            topic_id=topic_id,
            mastery_probability=Decimal("0.100"),
            confidence=Decimal("0.000"),
            evidence_count=0,
            state="UNKNOWN",
            model_version="bkt-v1",
        )
        db.add(state)
        await db.commit()
        await db.refresh(state)
    return state


async def get_or_create_memory_state(
    db: AsyncSession, user_id: uuid.UUID, topic_id: uuid.UUID
) -> MemoryState:
    stmt = select(MemoryState).where(
        MemoryState.user_id == user_id,
        MemoryState.topic_id == topic_id,
    )
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()
    if not state:
        state = MemoryState(
            user_id=user_id,
            topic_id=topic_id,
            stability=Decimal("1.00"),
            difficulty=Decimal("5.00"),
            retrievability=Decimal("1.000"),
            next_review_at=datetime.now(timezone.utc) + timedelta(days=1),
            fsrs_version="fsrs-v4",
        )
        db.add(state)
        await db.commit()
        await db.refresh(state)
    return state


async def get_or_create_confidence_state(
    db: AsyncSession, user_id: uuid.UUID, topic_id: uuid.UUID
) -> ConfidenceState:
    stmt = select(ConfidenceState).where(
        ConfidenceState.user_id == user_id,
        ConfidenceState.topic_id == topic_id,
    )
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()
    if not state:
        state = ConfidenceState(
            user_id=user_id,
            topic_id=topic_id,
            self_confidence=Decimal("0.500"),
        )
        db.add(state)
        await db.commit()
        await db.refresh(state)
    return state


async def process_knowledge_observation(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_id: uuid.UUID,
    is_correct: bool,
    response_time_seconds: Optional[int] = None,
) -> Tuple[MasteryState, MemoryState]:
    """
    Authoritative knowledge update via BKT and memory update via FSRS.
    Records append-only learner event and audit log.
    """
    mastery = await get_or_create_mastery_state(db, user_id, topic_id)
    memory = await get_or_create_memory_state(db, user_id, topic_id)

    old_mastery = float(mastery.mastery_probability)
    old_state = mastery.state

    # 1. Update BKT Knowledge State
    new_mastery = compute_bkt_posterior(old_mastery, is_correct)
    new_count = mastery.evidence_count + 1
    new_confidence = compute_confidence(new_count)
    new_state = classify_mastery_state(new_mastery, new_confidence, new_count)

    mastery.mastery_probability = Decimal(str(new_mastery))
    mastery.confidence = Decimal(str(new_confidence))
    mastery.evidence_count = new_count
    mastery.state = new_state
    mastery.last_assessed_at = datetime.now(timezone.utc)

    # 2. Update FSRS Memory State
    elapsed_days = max(
        0.05,
        (datetime.now(timezone.utc) - memory.updated_at).total_seconds() / 86400.0,
    )
    rating = 3 if is_correct else 1  # 3=Good if correct, 1=Again if incorrect
    new_s, new_d, new_r, interval_hours = update_fsrs_state(
        float(memory.stability), float(memory.difficulty), rating, elapsed_days
    )

    memory.stability = Decimal(str(new_s))
    memory.difficulty = Decimal(str(new_d))
    memory.retrievability = Decimal(str(new_r))
    memory.next_review_at = datetime.now(timezone.utc) + timedelta(hours=interval_hours)

    await db.commit()
    await db.refresh(mastery)
    await db.refresh(memory)

    # 3. Emit Learner Event (Append-only)
    event_payload = {
        "topic_id": str(topic_id),
        "is_correct": is_correct,
        "response_time_seconds": response_time_seconds,
        "old_mastery": old_mastery,
        "new_mastery": new_mastery,
        "old_state": old_state,
        "new_state": new_state,
        "stability_days": new_s,
        "next_review_at": memory.next_review_at.isoformat(),
    }

    event = LearnerEvent(
        user_id=user_id,
        event_type="MASTERY_UPDATED",
        entity_type="topic",
        entity_id=topic_id,
        evidence_category="KNOWLEDGE",
        payload=event_payload,
    )
    db.add(event)
    await db.commit()

    logger.info(
        "knowledge_observation_processed",
        user_id=str(user_id),
        topic_id=str(topic_id),
        new_mastery=new_mastery,
        new_state=new_state,
    )
    return mastery, memory


async def update_student_confidence(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_id: uuid.UUID,
    confidence_value: float,
) -> ConfidenceState:
    """Updates student self-reported confidence (0.0 to 1.0)."""
    conf_state = await get_or_create_confidence_state(db, user_id, topic_id)
    clamped_val = max(0.0, min(1.0, confidence_value))
    conf_state.self_confidence = Decimal(str(round(clamped_val, 3)))
    await db.commit()
    await db.refresh(conf_state)

    event = LearnerEvent(
        user_id=user_id,
        event_type="CONFIDENCE_UPDATED",
        entity_type="topic",
        entity_id=topic_id,
        evidence_category="SELF_REPORT",
        payload={"topic_id": str(topic_id), "self_confidence": clamped_val},
    )
    db.add(event)
    await db.commit()

    return conf_state


async def get_topic_learner_state(
    db: AsyncSession, user_id: uuid.UUID, topic_id: uuid.UUID
) -> Dict[str, Any]:
    """Assembles all intelligence dimensions for a topic."""
    mastery = await get_or_create_mastery_state(db, user_id, topic_id)
    memory = await get_or_create_memory_state(db, user_id, topic_id)
    confidence = await get_or_create_confidence_state(db, user_id, topic_id)

    # Compute live retrievability decay based on time elapsed since review
    elapsed_days = (datetime.now(timezone.utc) - memory.updated_at).total_seconds() / 86400.0
    current_retrievability = compute_retrievability(float(memory.stability), elapsed_days)

    calib_status, calib_desc = evaluate_confidence_calibration(
        float(confidence.self_confidence),
        float(mastery.mastery_probability),
        mastery.evidence_count,
    )

    gaps = await detect_knowledge_gaps(db, user_id, topic_id)
    prereq_blockers = await find_prerequisite_blockers(db, user_id, topic_id)

    return {
        "topic_id": topic_id,
        "mastery": {
            "probability": float(mastery.mastery_probability),
            "confidence": float(mastery.confidence),
            "evidence_count": mastery.evidence_count,
            "state": mastery.state,
            "model_version": mastery.model_version,
            "last_assessed_at": mastery.last_assessed_at,
        },
        "memory": {
            "stability_days": float(memory.stability),
            "difficulty": float(memory.difficulty),
            "retrievability": current_retrievability,
            "next_review_at": memory.next_review_at,
            "fsrs_version": memory.fsrs_version,
        },
        "confidence": {
            "self_confidence": float(confidence.self_confidence),
            "calibration_status": calib_status,
            "calibration_description": calib_desc,
        },
        "gaps": gaps,
        "prerequisite_blockers": prereq_blockers,
    }


async def apply_cold_start_diagnostic(
    db: AsyncSession,
    user_id: uuid.UUID,
    results: List[Dict[str, Any]],  # [{"topic_id": UUID, "is_correct": bool}]
) -> List[MasteryState]:
    """Applies a battery of diagnostic questions to initialize cold-start knowledge."""
    updated_states = []
    for item in results:
        topic_id = uuid.UUID(str(item["topic_id"]))
        is_correct = bool(item.get("is_correct", False))
        mst, _ = await process_knowledge_observation(db, user_id, topic_id, is_correct)
        updated_states.append(mst)
    return updated_states
