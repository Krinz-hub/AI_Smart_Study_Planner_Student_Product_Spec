import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.database import get_db
from app.learner.schemas import (
    LearnerEventCreate,
    LearnerEventResponse,
    LearnerFeedbackRequest,
    TopicEvidenceResponse,
    ConfidenceUpdateRequest,
    KnowledgeObservationRequest,
    DiagnosticBatchRequest,
    TopicLearnerStateResponse,
)
from app.learner.event_service import (
    record_event,
    submit_feedback,
    get_topic_evidence,
    list_recent_events,
)
from app.learner.intelligence_service import (
    process_knowledge_observation,
    update_student_confidence,
    get_topic_learner_state,
    apply_cold_start_diagnostic,
)
from app.learner.gaps import detect_knowledge_gaps

router = APIRouter(prefix="/learner", tags=["learner"])


@router.post("/feedback", response_model=LearnerEventResponse, status_code=status.HTTP_201_CREATED)
async def post_feedback(
    req: LearnerFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LearnerEventResponse:
    event = await submit_feedback(db, current_user.id, req)
    return LearnerEventResponse.model_validate(event)


@router.get("/topics/{topic_id}", response_model=TopicLearnerStateResponse)
async def get_topic_state(
    topic_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicLearnerStateResponse:
    state = await get_topic_learner_state(db, current_user.id, topic_id)
    return TopicLearnerStateResponse(**state)


@router.get("/topics/{topic_id}/evidence", response_model=TopicEvidenceResponse)
async def get_evidence(
    topic_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicEvidenceResponse:
    return await get_topic_evidence(db, current_user.id, topic_id)


@router.get("/topics/{topic_id}/gaps")
async def get_topic_gaps(
    topic_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    return await detect_knowledge_gaps(db, current_user.id, topic_id)


@router.post("/topics/{topic_id}/confidence")
async def set_confidence(
    topic_id: uuid.UUID,
    req: ConfidenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    conf_state = await update_student_confidence(db, current_user.id, topic_id, req.self_confidence)
    return {
        "status": "success",
        "topic_id": topic_id,
        "self_confidence": float(conf_state.self_confidence),
    }


@router.post("/topics/{topic_id}/observation")
async def record_observation(
    topic_id: uuid.UUID,
    req: KnowledgeObservationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    mst, mem = await process_knowledge_observation(
        db, current_user.id, topic_id, req.is_correct, req.response_time_seconds
    )
    return {
        "status": "success",
        "topic_id": topic_id,
        "mastery_probability": float(mst.mastery_probability),
        "confidence": float(mst.confidence),
        "state": mst.state,
        "stability_days": float(mem.stability),
        "next_review_at": mem.next_review_at,
    }


@router.post("/diagnostic")
async def post_diagnostic(
    req: DiagnosticBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    results = [r.model_dump() for r in req.results]
    updated = await apply_cold_start_diagnostic(db, current_user.id, results)
    return {
        "status": "success",
        "topics_updated": len(updated),
    }


@router.get("/events", response_model=List[LearnerEventResponse])
async def get_events(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[LearnerEventResponse]:
    events = await list_recent_events(db, current_user.id, limit=limit)
    return [LearnerEventResponse.model_validate(e) for e in events]


@router.post("/events", response_model=LearnerEventResponse, status_code=status.HTTP_201_CREATED)
async def post_event(
    req: LearnerEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LearnerEventResponse:
    event = await record_event(db, current_user.id, req)
    return LearnerEventResponse.model_validate(event)
