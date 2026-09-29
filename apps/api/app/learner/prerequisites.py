import uuid
from typing import Any, Dict, List, Set, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academics.models import TopicRelationship, Topic
from app.learner.models import MasteryState


async def find_prerequisite_blockers(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_id: uuid.UUID,
    mastery_threshold: float = 0.60,
) -> List[Dict[str, Any]]:
    """
    Finds direct prerequisite topics that have insufficient mastery (< 0.60).
    Returns list of blocking topics with their names and current mastery.
    """
    stmt = (
        select(TopicRelationship, Topic)
        .join(Topic, Topic.id == TopicRelationship.source_topic_id)
        .where(
            TopicRelationship.target_topic_id == topic_id,
            TopicRelationship.relationship_type == "prerequisite",
        )
    )
    result = await db.execute(stmt)
    prereqs = list(result.all())

    blockers = []
    for rel, prereq_topic in prereqs:
        mst_stmt = select(MasteryState).where(
            MasteryState.user_id == user_id,
            MasteryState.topic_id == prereq_topic.id,
        )
        mst_res = await db.execute(mst_stmt)
        mstate = mst_res.scalar_one_or_none()

        mastery_val = float(mstate.mastery_probability) if mstate else 0.10
        state_label = mstate.state if mstate else "UNKNOWN"

        if mastery_val < mastery_threshold or state_label in ("CRITICAL", "WEAK", "UNKNOWN"):
            blockers.append({
                "topic_id": prereq_topic.id,
                "topic_name": prereq_topic.name,
                "mastery_probability": mastery_val,
                "state": state_label,
                "confidence": float(rel.confidence),
            })

    return blockers
