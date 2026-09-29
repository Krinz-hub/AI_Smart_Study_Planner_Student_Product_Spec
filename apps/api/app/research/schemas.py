from typing import List, Optional
from pydantic import BaseModel, Field


class WebSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    limit: int = Field(default=5, ge=1, le=20)


class WebSearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str
    source: str


class WebSearchResponse(BaseModel):
    query: str
    results: List[WebSearchResultItem]
    provider: str


class SafeFetchRequest(BaseModel):
    url: str = Field(..., description="Target URL to fetch securely")


class SafeFetchResponse(BaseModel):
    url: str
    status: str
    content_snippet: str
