import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class QuizGenerateRequest(BaseModel):
    topic_id: uuid.UUID
    num_questions: int = Field(default=5, ge=1, le=20)
    difficulty: str = Field(default="MEDIUM", pattern="^(EASY|MEDIUM|HARD)$")


class QuestionOptionResponse(BaseModel):
    key: str
    text: str


class QuestionStudentView(BaseModel):
    id: uuid.UUID
    question_text: str
    question_type: str
    difficulty: str
    options: Optional[List[QuestionOptionResponse]] = None


class QuizResponse(BaseModel):
    quiz_id: uuid.UUID
    id: Optional[uuid.UUID] = None
    topic_id: uuid.UUID
    status: str
    total_questions: int
    questions: List[QuestionStudentView]

    @model_validator(mode="before")
    @classmethod
    def populate_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            qid = data.get("quiz_id") or data.get("id")
            if qid:
                data["quiz_id"] = qid
                data["id"] = qid
        elif hasattr(data, "quiz_id") or hasattr(data, "id"):
            qid = getattr(data, "quiz_id", None) or getattr(data, "id", None)
            return {
                "quiz_id": qid,
                "id": qid,
                "topic_id": getattr(data, "topic_id", None),
                "status": getattr(data, "status", None),
                "total_questions": getattr(data, "total_questions", None),
                "questions": getattr(data, "questions", []),
            }
        return data


class QuizAnswerSubmission(BaseModel):
    question_id: uuid.UUID
    answer: Optional[Dict[str, Any]] = None
    selected_key: Optional[str] = None
    response_time_seconds: Optional[int] = Field(None, ge=0)

    @model_validator(mode="before")
    @classmethod
    def populate_answer(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("answer") and data.get("selected_key"):
                data["answer"] = {"key": data["selected_key"]}
            elif data.get("answer") and isinstance(data["answer"], dict) and "key" in data["answer"] and not data.get("selected_key"):
                data["selected_key"] = data["answer"]["key"]
            elif not data.get("answer") and not data.get("selected_key"):
                data["answer"] = {"key": "A"}
        return data


class QuizSubmitRequest(BaseModel):
    answers: List[QuizAnswerSubmission]
    time_spent_seconds: Optional[int] = Field(default=0, ge=0)


class QuestionResultItem(BaseModel):
    question_id: uuid.UUID
    question_text: str
    student_answer: Dict[str, Any]
    correct_answer: Dict[str, Any]
    is_correct: bool
    explanation: str


class QuizResultResponse(BaseModel):
    quiz_id: uuid.UUID
    topic_id: uuid.UUID
    score: float
    accuracy: float
    total_questions: int
    correct_count: int
    time_spent_seconds: int
    weak_concepts: List[str]
    strong_concepts: List[str]
    recommended_next_action: str
    questions: List[QuestionResultItem]
