import uuid
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learner.models import MasteryState, MemoryState, LearnerEvent
from app.learner.prerequisites import find_prerequisite_blockers


async def detect_knowledge_gaps(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_id: uuid.UUID,
) -> List[Dict[str, Any]]:
    """
    Classifies active knowledge gaps for a topic per 04_LEARNER_INTELLIGENCE.md.
    """
    gaps: List[Dict[str, Any]] = []

    # 1. Fetch Mastery
    mst_stmt = select(MasteryState).where(
        MasteryState.user_id == user_id,
        MasteryState.topic_id == topic_id,
    )
    mst_res = await db.execute(mst_stmt)
    mastery = mst_res.scalar_one_or_none()

    # 2. Fetch Memory
    mem_stmt = select(MemoryState).where(
        MemoryState.user_id == user_id,
        MemoryState.topic_id == topic_id,
    )
    mem_res = await db.execute(mem_stmt)
    memory = mem_res.scalar_one_or_none()

    # Gap: UNASSESSED
    if not mastery or mastery.evidence_count == 0 or mastery.state == "UNKNOWN":
        gaps.append({
            "gap_type": "UNASSESSED",
            "severity": "medium",
            "description": "Topic has not been assessed yet. Diagnostic or quiz recommended.",
        })
    else:
        # Gap: LOW_MASTERY
        if float(mastery.mastery_probability) < 0.60:
            gaps.append({
                "gap_type": "LOW_MASTERY",
                "severity": "high" if float(mastery.mastery_probability) < 0.35 else "medium",
                "description": f"Mastery probability ({float(mastery.mastery_probability):.0%}) is below proficiency threshold.",
            })

    # Gap: FORGOTTEN (Retrievability dropped)
    if memory and float(memory.retrievability) < 0.70:
        gaps.append({
            "gap_type": "FORGOTTEN",
            "severity": "high" if float(memory.retrievability) < 0.50 else "medium",
            "description": f"Memory retrievability has decayed to {float(memory.retrievability):.0%}. Revision required.",
        })

    # Gap: PREREQUISITE_GAP
    blockers = await find_prerequisite_blockers(db, user_id, topic_id)
    if blockers:
        gaps.append({
            "gap_type": "PREREQUISITE_GAP",
            "severity": "high",
            "description": f"{len(blockers)} foundational prerequisite topic(s) require mastery before advancing.",
            "blockers": blockers,
        })

    # Gap: REPEATED_MISTAKES
    # Query recent quiz/assessment events for consecutive errors
    topic_str = str(topic_id)
    recent_events_stmt = (
        select(LearnerEvent)
        .where(
            LearnerEvent.user_id == user_id,
            LearnerEvent.evidence_category == "KNOWLEDGE",
            LearnerEvent.payload["topic_id"].as_string() == topic_str,
        )
        .order_by(LearnerEvent.created_at.desc())
        .limit(3)
    )
    rev_res = await db.execute(recent_events_stmt)
    recent_events = list(rev_res.scalars().all())

    if len(recent_events) >= 2 and all(not e.payload.get("is_correct", False) for e in recent_events):
        gaps.append({
            "gap_type": "REPEATED_MISTAKES",
            "severity": "high",
            "description": "Student has made repeated incorrect attempts in recent assessments.",
        })

    return gaps
