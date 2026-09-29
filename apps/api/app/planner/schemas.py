import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PlanGenerateRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    daily_capacity_minutes: int = Field(default=240, ge=30, le=720)


class StudyTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    topic_id: uuid.UUID
    title: str
    objective: str
    task_type: str
    planned_start: datetime
    planned_end: datetime
    duration_minutes: int
    priority: float
    status: str
    locked: bool
    reason: Dict[str, Any]
    plan_version: str
    created_at: datetime


class PlanResponse(BaseModel):
    plan_id: str
    plan_version: str
    start_date: date
    end_date: date
    total_tasks: int
    total_minutes: int
    tasks: List[StudyTaskResponse]


class TaskLockRequest(BaseModel):
    locked: bool = True


class TaskRescheduleRequest(BaseModel):
    new_start: datetime


class TaskCompleteRequest(BaseModel):
    actual_minutes: Optional[int] = Field(default=45, ge=1, le=480)
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    is_correct: Optional[bool] = None
    self_rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    notes: Optional[str] = None
    auto_replan: bool = False


class TaskSkipRequest(BaseModel):
    reason: Optional[str] = Field(default="not_enough_time")
    auto_replan: bool = False


class PlanReplanRequest(BaseModel):
    reason: str = Field(description="Reason for replanning, e.g., TASK_SKIPPED, ASSESSMENT_RESULT")
    context: Optional[Dict[str, Any]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    daily_capacity_minutes: int = Field(default=240, ge=30, le=720)


class TaskCompletionResult(BaseModel):
    task: StudyTaskResponse
    bkt_mastery_probability: Optional[float] = None
    bkt_state: Optional[str] = None
    fsrs_retrievability: Optional[float] = None
    replanned: bool = False


class StudySessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    actual_minutes: int
    completion_status: str
    self_rating: Optional[float] = None

