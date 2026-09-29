import uuid
from datetime import datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StudentProfileBase(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    semester: Optional[str] = None
    branch: Optional[str] = None
    timezone: str = "UTC"


class StudentProfileUpdate(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    semester: Optional[str] = None
    branch: Optional[str] = None
    timezone: Optional[str] = None


class StudentProfileResponse(StudentProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class AvailabilityWindowBase(BaseModel):
    weekday: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: time
    end_time: time
    enabled: bool = True


class AvailabilityWindowCreate(AvailabilityWindowBase):
    pass


class AvailabilityWindowResponse(AvailabilityWindowBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID


class AvailabilityBatchUpdate(BaseModel):
    windows: List[AvailabilityWindowCreate]


class GoalBase(BaseModel):
    subject_id: Optional[uuid.UUID] = None
    topic_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=1, max_length=200)
    target_type: str = "mastery"
    target_value: Optional[Decimal] = None
    deadline: Optional[datetime] = None
    priority: Decimal = Decimal("1.0")
    status: str = "active"


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    target_type: Optional[str] = None
    target_value: Optional[Decimal] = None
    deadline: Optional[datetime] = None
    priority: Optional[Decimal] = None
    status: Optional[str] = None


class GoalResponse(GoalBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime


class StudentStateResponse(BaseModel):
    """Authoritative assembled read-only student state per 03_API_CONTRACT.md"""
    profile: Optional[StudentProfileResponse]
    subjects: List[Dict[str, Any]]
    topics: List[Dict[str, Any]]
    mastery: List[Dict[str, Any]]
    memory: List[Dict[str, Any]]
    goals: List[GoalResponse]
    availability: List[AvailabilityWindowResponse]
    exams: List[Dict[str, Any]]


class TopicMasteryOverview(BaseModel):
    id: uuid.UUID
    name: str
    subject_id: uuid.UUID
    subject_name: str
    subject_color: str = "#3b82f6"
    mastery_probability: float
    state: str
    retrievability: Optional[float] = None
    next_review_at: Optional[datetime] = None


class ProgressOverviewResponse(BaseModel):
    overall_mastery_pct: float
    total_subjects: int
    total_topics: int
    mastered_topics_count: int
    strong_topics: List[TopicMasteryOverview]
    developing_topics: List[TopicMasteryOverview]
    needs_attention_topics: List[TopicMasteryOverview]
    review_due_topics: List[TopicMasteryOverview]
    total_study_minutes_completed: int
    streak_days: int = 1


class StudentSuggestion(BaseModel):
    id: str
    title: str
    subject_name: str
    topic_name: Optional[str] = None
    action_type: str  # STUDY, PRACTICE, REVIEW
    priority: str  # HIGH, MEDIUM, LOW
    reason: str


class StudentSuggestionsResponse(BaseModel):
    suggestions: List[StudentSuggestion]


class StudentTaskSummary(BaseModel):
    id: uuid.UUID
    title: str
    subject_name: str
    topic_name: Optional[str] = None
    duration_minutes: int
    task_type: str
    status: str
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None


class StudentHomeResponse(BaseModel):
    student_name: str
    academic_summary: str
    onboarding_completed: bool
    top_task: Optional[StudentTaskSummary] = None
    top_task_reason: Optional[str] = None
    next_task: Optional[StudentTaskSummary] = None
    today_completed_minutes: int = 0
    today_target_minutes: int = 180
    tasks_completed_today: int = 0
    tasks_total_today: int = 0
    subjects_count: int = 0
    overall_mastery_pct: float = 0.0
    streak_days: int = 1

