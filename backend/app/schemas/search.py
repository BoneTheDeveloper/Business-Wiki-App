"""Search and chat Pydantic schemas."""
from pydantic import BaseModel
from typing import Optional, List


class SearchRequest(BaseModel):
    """Semantic search request."""
    query: str
    top_k: int = 10
    document_ids: Optional[List[str]] = None
    filters: Optional[dict] = None


class SearchResult(BaseModel):
    """Single search result."""
    chunk_id: str
    content: str
    metadata: dict
    document_id: str
    filename: str
    format: str
    similarity: float


class SearchResponse(BaseModel):
    """Search response with results."""
    query: str
    results: List[SearchResult]
    total: int


class ChatMessage(BaseModel):
    """Chat message in conversation."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Chat request with optional context."""
    query: str
    document_ids: Optional[List[str]] = None
    conversation_history: Optional[List[ChatMessage]] = None
    top_k: int = 5


class ChatSource(BaseModel):
    """Source citation in chat response."""
    document_id: str
    filename: str
    chunk_id: str
    similarity: float
    page: Optional[int] = None


class ChatResponse(BaseModel):
    """Chat response with sources."""
    answer: str
    sources: List[ChatSource]
    model: str
    usage: dict
