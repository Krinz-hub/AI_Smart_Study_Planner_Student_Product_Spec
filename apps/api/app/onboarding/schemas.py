import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AcademicTypeEnum(str, Enum):
    SCHOOL = "SCHOOL"
    COLLEGE = "COLLEGE"
    COMPETITIVE_EXAM = "COMPETITIVE_EXAM"
    OTHER = "OTHER"


class OnboardingStepEnum(str, Enum):
    ACADEMIC_TYPE = "ACADEMIC_TYPE"
    ACADEMIC_PROFILE = "ACADEMIC_PROFILE"
    ACADEMIC_DISCOVERY = "ACADEMIC_DISCOVERY"
    SYLLABUS_REVIEW = "SYLLABUS_REVIEW"
    GOALS_EXAMS = "GOALS_EXAMS"
    AVAILABILITY = "AVAILABILITY"
    DIAGNOSTIC = "DIAGNOSTIC"
    COMPLETED = "COMPLETED"


class SelectAcademicTypeRequest(BaseModel):
    academic_type: AcademicTypeEnum = Field(..., description="Educational track category")


class SchoolProfileDetails(BaseModel):
    country: str = Field(default="India")
    board: str = Field(..., description="Educational board, e.g. CBSE, ICSE, State Board, IB")
    grade: str = Field(..., description="Grade/class, e.g. Class 11, Class 12")
    school_name: Optional[str] = None
    academic_year: Optional[str] = None


class CollegeProfileDetails(BaseModel):
    country: str = Field(default="India")
    university: str = Field(..., description="University name, e.g. Anna University, VTU, Mumbai University")
    college: Optional[str] = None
    degree: str = Field(..., description="Degree program, e.g. B.Tech, B.E., B.Sc, BCA, MBBS")
    branch: str = Field(..., description="Branch or major, e.g. Computer Science, Mechanical")
    year: int = Field(..., ge=1, le=6, description="Academic year (1-6)")
    semester: int = Field(..., ge=1, le=12, description="Current semester (1-12)")
    academic_year: Optional[str] = None


class CompetitiveExamProfileDetails(BaseModel):
    exam_name: str = Field(..., description="Target exam, e.g. JEE Main, NEET, GATE, UPSC, GRE")
    target_year: int = Field(..., ge=2024, le=2035)
    attempt: Optional[int] = Field(default=1, ge=1)
    subjects: Optional[List[str]] = None


class OtherProfileDetails(BaseModel):
    description: str = Field(..., min_length=2)
    focus_areas: Optional[List[str]] = None


class AcademicProfileRequest(BaseModel):
    details: Dict[str, Any] = Field(..., description="Academic profile attributes matching academic type")


class OnboardingStatusResponse(BaseModel):
    user_id: uuid.UUID
    current_step: str
    academic_type: Optional[str] = None
    academic_details: Dict[str, Any] = Field(default_factory=dict)
    discovered_syllabus: Optional[Dict[str, Any]] = None
    is_completed: bool = False
    updated_at: Optional[datetime] = None


class DiscoveredUnit(BaseModel):
    unit_number: int
    title: str
    topics: List[str] = Field(default_factory=list)


class DiscoveredSubject(BaseModel):
    name: str
    code: Optional[str] = None
    color_code: str = "#3b82f6"
    units: List[DiscoveredUnit] = Field(default_factory=list)


class DiscoveredSyllabusResponse(BaseModel):
    academic_summary: str
    confidence_score: float
    sources: List[Dict[str, str]] = Field(default_factory=list)
    subjects: List[DiscoveredSubject]
    institution_verified: bool = True
    institution_name: Optional[str] = None
    verification_status: str = "VERIFIED"  # "VERIFIED" | "UNVERIFIED"
    verification_note: Optional[str] = None
    warning_flag: Optional[str] = None


class SubjectConfirmationItem(BaseModel):
    name: str = Field(..., min_length=1)
    code: Optional[str] = None
    color_code: Optional[str] = "#3b82f6"
    topics: List[str] = Field(..., min_length=1, description="List of topic names for this subject")


class ConfirmSyllabusRequest(BaseModel):
    subjects: List[SubjectConfirmationItem] = Field(..., min_length=1)


class ConfirmSyllabusResponse(BaseModel):
    status: str = "success"
    subjects_created: int
    topics_created: int
    current_step: str = "GOALS_EXAMS"


class GoalInput(BaseModel):
    title: str = Field(..., min_length=2)
    target_type: str = Field(default="mastery", description="mastery, study_hours, exam_score")
    target_value: Optional[float] = Field(default=0.85, ge=0.0, le=100.0)
    subject_id: Optional[uuid.UUID] = None
    deadline: Optional[datetime] = None
    priority: float = Field(default=1.0, ge=0.1, le=10.0)


class ExamInput(BaseModel):
    name: str = Field(..., min_length=2)
    subject_id: Optional[uuid.UUID] = None
    exam_at: datetime


class WeeklyAvailabilityDay(BaseModel):
    weekday: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: str = Field(default="09:00", description="HH:MM")
    end_time: str = Field(default="13:00", description="HH:MM")
    enabled: bool = True


class SetupGoalsAndAvailabilityRequest(BaseModel):
    daily_capacity_minutes: int = Field(default=180, ge=30, le=720)
    study_time_preference: str = Field(default="evening", description="morning, afternoon, evening, night")
    exams: List[ExamInput] = Field(default_factory=list)
    goals: List[GoalInput] = Field(default_factory=list)
    weekly_availability: List[WeeklyAvailabilityDay] = Field(default_factory=list)


class SetupGoalsAndAvailabilityResponse(BaseModel):
    status: str = "success"
    exams_created: int
    goals_created: int
    availability_slots_created: int
    daily_capacity_minutes: int
    current_step: str = "DIAGNOSTIC"


class DiagnosticOption(BaseModel):
    key: str
    text: str


class DiagnosticQuestion(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    topic_name: str
    subject_name: str
    question_text: str
    difficulty: str = "MEDIUM"
    options: List[DiagnosticOption]


class DiagnosticGenerateResponse(BaseModel):
    status: str = "success"
    total_questions: int
    questions: List[DiagnosticQuestion]


class DiagnosticAnswerSubmission(BaseModel):
    question_id: uuid.UUID
    selected_key: str
    response_time_seconds: Optional[int] = 10


class DiagnosticSubmitRequest(BaseModel):
    answers: List[DiagnosticAnswerSubmission] = Field(..., min_length=1)


class TopicMasteryResult(BaseModel):
    topic_id: uuid.UUID
    topic_name: str
    mastery_probability: float
    state: str


class DiagnosticSubmitResponse(BaseModel):
    status: str = "success"
    total_answered: int
    correct_count: int
    accuracy_pct: float
    topic_masteries: List[TopicMasteryResult]
    plan_tasks_scheduled: int
    current_step: str = "COMPLETED"
    is_completed: bool = True

