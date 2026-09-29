import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SubjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=30)


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = None
    color: Optional[str] = None


class SubjectResponse(SubjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TopicBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_topic_id: Optional[uuid.UUID] = None
    syllabus_weight: Optional[Decimal] = Decimal("1.0")


class TopicCreate(TopicBase):
    pass


class TopicUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_topic_id: Optional[uuid.UUID] = None
    syllabus_weight: Optional[Decimal] = None


class TopicResponse(TopicBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TopicRelationshipCreate(BaseModel):
    target_topic_id: uuid.UUID
    relationship_type: str = Field(
        ...,
        pattern="^(prerequisite|related_to|part_of)$",
        description="Allowed: prerequisite, related_to, part_of",
    )
    confidence: Decimal = Field(default=Decimal("1.0"), ge=0.0, le=1.0)
    source: str = "manual"


class TopicRelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_topic_id: uuid.UUID
    target_topic_id: uuid.UUID
    relationship_type: str
    confidence: Decimal
    source: str
    created_at: datetime


class ExamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    subject_id: uuid.UUID
    exam_at: datetime


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    name: Optional[str] = None
    exam_at: Optional[datetime] = None


class ExamResponse(ExamBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
