import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExamModeGenerateRequest(BaseModel):
    exam_id: uuid.UUID
    workload_ceiling_minutes: int = Field(default=360, ge=60, le=720)
    include_rescue_recovery: bool = True


class ExamRescueAction(BaseModel):
    action_type: str  # DROP_LOW_PRIORITY, DEFER_NON_EXAM, PRESERVE_CRITICAL, RESCHEDULE_BACKLOG
    topic_name: str
    reason: str


class ExamPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exam_id: uuid.UUID
    subject_id: uuid.UUID
    status: str
    total_topics_covered: int
    syllabus_coverage_pct: float
    target_exam_date: datetime
    daily_workload_minutes: int
    workload_ceiling_minutes: int
    rescue_actions: List[ExamRescueAction]
    tasks: List[Dict[str, Any]]
    created_at: datetime


class ExamPlanActionRequest(BaseModel):
    action: str = Field(..., pattern="^(ACCEPT|CUSTOMIZE|DISMISS)$")
    custom_daily_workload_minutes: Optional[int] = Field(None, ge=60, le=720)
