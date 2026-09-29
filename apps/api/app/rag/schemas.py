import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RetrievalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    subject_id: Optional[uuid.UUID] = Field(None, description="Optional subject filter")
    topic_id: Optional[uuid.UUID] = Field(None, description="Optional topic filter")
    limit: int = Field(default=8, ge=1, le=50, description="Max number of sources to return")


class SourceCitation(BaseModel):
    source_id: str
    document_id: uuid.UUID
    document_title: str
    page_number: Optional[int]
    section_path: Optional[str]
    chunk_index: int
    snippet: str
    relevance_score: float


class RetrievalSearchResponse(BaseModel):
    query: str
    sufficiency: str  # SUFFICIENT, PARTIAL, INSUFFICIENT, CONFLICTING
    sources: List[SourceCitation]
    total_candidates: int
