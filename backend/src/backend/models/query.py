
from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class AskRequest(QueryRequest):
    # Omit to start a new conversation; the response returns the new session_id.
    session_id: UUID | None = None


class SearchResult(BaseModel):
    chunk_id: int
    item_id: int
    title: str
    source_url: str | None
    content: str
    distance: float
    similarity: float


class QueryResponse(BaseModel):
    question: str
    total_results: int
    results: list[SearchResult]

class CitationResponse(BaseModel):
    source_label: str
    chunk_id: int
    item_id: int
    title: str
    source_url: str | None
    content: str


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: list[CitationResponse]
    session_id: UUID | None = None
