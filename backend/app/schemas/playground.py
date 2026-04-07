"""Playground API schemas for RAG observability."""
from pydantic import BaseModel
from typing import Optional, List


class PlaygroundSearchRequest(BaseModel):
    """Search request for playground."""
    query: str
    top_k: int = 10
    document_ids: Optional[List[str]] = None


class PlaygroundChatRequest(BaseModel):
    """Chat request for playground with conversation history."""
    query: str
    top_k: int = 5
    document_ids: Optional[List[str]] = None
    conversation_history: Optional[List[dict]] = None


class PlaygroundChunkResult(BaseModel):
    """Retrieved chunk with similarity score."""
    chunk_id: str
    content: str
    metadata: dict
    document_id: str
    filename: str
    format: str
    similarity: float


class PlaygroundStepMetrics(BaseModel):
    """Latency metrics for a single pipeline step."""
    latency_ms: float


class PlaygroundEmbeddingMetrics(PlaygroundStepMetrics):
    """Embedding step metrics."""
    dimensions: int = 1536


class PlaygroundRetrievalMetrics(PlaygroundStepMetrics):
    """Retrieval step metrics."""
    chunks_count: int = 0


class PlaygroundGenerationMetrics(PlaygroundStepMetrics):
    """LLM generation step metrics."""
    tokens_in: int = 0
    tokens_out: int = 0


class PlaygroundStepsDetail(BaseModel):
    """Detailed step-by-step pipeline metrics."""
    embedding: PlaygroundEmbeddingMetrics
    retrieval: PlaygroundRetrievalMetrics
    generation: PlaygroundGenerationMetrics


class PlaygroundSearchResponse(BaseModel):
    """Search response with chunks and metrics."""
    query: str
    chunks: List[PlaygroundChunkResult]
    steps: PlaygroundStepsDetail
    total_latency_ms: float


class PlaygroundChatSource(BaseModel):
    """Source citation in playground chat response."""
    document_id: str
    filename: str
    chunk_id: str
    similarity: float
    page: Optional[int] = None


class PlaygroundChatResponse(BaseModel):
    """Chat response with full RAG pipeline observability."""
    response: str
    chunks: List[PlaygroundChunkResult]
    sources: List[PlaygroundChatSource]
    steps: PlaygroundStepsDetail
    model: str
    total_latency_ms: float


class PlaygroundDocumentInfo(BaseModel):
    """Document info for playground listing."""
    id: str
    filename: str
    format: str
    status: str
    chunk_count: int


class PlaygroundDocumentsResponse(BaseModel):
    """List of available documents for playground."""
    documents: List[PlaygroundDocumentInfo]
    total: int
