import uuid
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class Recommendation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: Optional[uuid.UUID] = None
    topic_name: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    subject_name: Optional[str] = None
    priority: float = Field(..., ge=0.0, le=1.0)
    action: str = Field(
        ...,
        description="Candidate intervention: LEARN, PRACTICE, REVISE, RETRIEVE, QUIZ, REVIEW_MISTAKES, PREREQUISITE_REPAIR, DEEP_STUDY, QUICK_REVISION, REST, NO_ACTION",
    )
    reason: List[str]
    evidence_ids: List[uuid.UUID] = Field(default_factory=list)
    algorithm_version: str = "priority-v1"


class CandidateDecisionsResponse(BaseModel):
    recommendations: List[Recommendation]
    top_recommendation: Optional[Recommendation]
    algorithm_version: str = "priority-v1"
