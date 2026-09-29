import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    processing_status: str
    content_hash: str
    filename: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    subject_id: Optional[uuid.UUID]
    filename: str
    content_hash: str
    version: int
    mime_type: str
    size_bytes: int
    processing_status: str
    processing_version: str
    error_message: Optional[str]
    chunk_count: int = 0
    created_at: datetime


class DocumentStatusResponse(BaseModel):
    document_id: uuid.UUID
    processing_status: str
    chunk_count: int
    error_message: Optional[str] = None


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    text: str
    page_number: Optional[int]
    section_path: Optional[str]
    metadata_json: Dict[str, Any]
    created_at: datetime


class DefinitionItem(BaseModel):
    term: str
    definition: str


class FormulaItem(BaseModel):
    name: str
    formula: str
    description: str


class ActiveRecallItem(BaseModel):
    question: str
    answer: str


class Document10PointSummary(BaseModel):
    document_id: uuid.UUID
    filename: str
    executive_summary: str
    key_definitions: List[DefinitionItem] = Field(default_factory=list)
    formulas_and_equations: List[FormulaItem] = Field(default_factory=list)
    core_mechanisms: List[str] = Field(default_factory=list)
    step_by_step_procedures: List[str] = Field(default_factory=list)
    common_pitfalls: List[str] = Field(default_factory=list)
    practical_examples: List[str] = Field(default_factory=list)
    high_yield_exam_points: List[str] = Field(default_factory=list)
    prerequisites_and_connections: List[str] = Field(default_factory=list)
    active_recall_questions: List[ActiveRecallItem] = Field(default_factory=list)
    generated_at: Optional[datetime] = None


class FlashcardItem(BaseModel):
    id: str
    front: str
    back: str
    tag: str
    difficulty: str = "MEDIUM"


class DocumentFlashcardsResponse(BaseModel):
    document_id: uuid.UUID
    total_flashcards: int
    flashcards: List[FlashcardItem]


class NoteGroundedQuizGenerateRequest(BaseModel):
    num_questions: int = Field(default=5, ge=1, le=20)
    difficulty: str = Field(default="MEDIUM", description="EASY, MEDIUM, HARD")

