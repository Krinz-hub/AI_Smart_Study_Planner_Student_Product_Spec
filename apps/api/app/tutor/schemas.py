import uuid
from typing import Any, List, Optional
from pydantic import BaseModel, Field, model_validator
from app.rag.schemas import SourceCitation


class TutorChatRequest(BaseModel):
    topic_id: uuid.UUID
    mode: str = Field(
        default="socratic",
        pattern="^(explain_simply|explain_in_detail|give_example|exam_answer|hint|correct_my_answer|socratic|eli5|deep_dive|exam_rubric)$",
        description="Pedagogical tutor mode",
    )
    message: str = Field(..., min_length=1, description="Student's query or response")

    @model_validator(mode="before")
    @classmethod
    def normalize_mode(cls, data: Any) -> Any:
        if isinstance(data, dict):
            m = data.get("mode", "socratic")
            mapping = {
                "eli5": "explain_simply",
                "deep_dive": "explain_in_detail",
                "exam_rubric": "exam_answer",
                "example": "give_example",
            }
            if m in mapping:
                data["mode"] = mapping[m]
        return data


class TutorChatResponse(BaseModel):
    topic_id: uuid.UUID
    mode: str
    response_text: str
    sources: List[SourceCitation]
    evidence_sufficiency: str
    pedagogical_intent: str
    suggested_followups: List[str]
