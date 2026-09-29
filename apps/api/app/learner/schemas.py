import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class LearnerEventBase(BaseModel):
    event_type: str = Field(..., max_length=64)
    entity_type: str = Field(..., max_length=64)
    entity_id: Optional[uuid.UUID] = None
    evidence_category: str = Field("BEHAVIOR", pattern="^(KNOWLEDGE|BEHAVIOR|SELF_REPORT|SYSTEM)$")
    idempotency_key: Optional[str] = Field(None, max_length=128)
    payload: Dict[str, Any] = Field(default_factory=dict)


class LearnerEventCreate(LearnerEventBase):
    pass


class LearnerEventResponse(LearnerEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime


class LearnerFeedbackRequest(BaseModel):
    topic_id: Optional[uuid.UUID] = None
    task_id: Optional[uuid.UUID] = None
    feedback_type: str = Field(
        ...,
        pattern="^(too_easy|too_hard|too_long|wrong_topic|bad_time|not_relevant|useful)$",
        description="Allowed feedback types: too_easy, too_hard, too_long, wrong_topic, bad_time, not_relevant, useful",
    )
    notes: Optional[str] = None


class TopicEvidenceResponse(BaseModel):
    topic_id: uuid.UUID
    knowledge_evidence: List[LearnerEventResponse]
    behavior_evidence: List[LearnerEventResponse]
    self_report_evidence: List[LearnerEventResponse]
    total_evidence_count: int


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    actor_type: str
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID]
    metadata_json: Dict[str, Any]
    created_at: datetime


class ConfidenceUpdateRequest(BaseModel):
    self_confidence: float = Field(..., ge=0.0, le=1.0, description="Self confidence rating from 0.0 to 1.0")


class KnowledgeObservationRequest(BaseModel):
    is_correct: bool
    response_time_seconds: Optional[int] = Field(None, ge=0)


class DiagnosticItem(BaseModel):
    topic_id: uuid.UUID
    is_correct: bool


class DiagnosticBatchRequest(BaseModel):
    results: List[DiagnosticItem]


class TopicLearnerStateResponse(BaseModel):
    topic_id: uuid.UUID
    mastery: Dict[str, Any]
    memory: Dict[str, Any]
    confidence: Dict[str, Any]
    gaps: List[Dict[str, Any]]
    prerequisite_blockers: List[Dict[str, Any]]
