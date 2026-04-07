"""Pydantic models matching backend playground API schemas exactly."""
from pydantic import BaseModel
from typing import Optional, List


class ChunkResult(BaseModel):
    """Retrieved chunk with similarity score."""
    chunk_id: str
    content: str
    metadata: dict
    document_id: str
    filename: str
    format: str
    similarity: float


class EmbeddingMetrics(BaseModel):
    """Embedding step metrics."""
    latency_ms: float
    dimensions: int = 1536


class RetrievalMetrics(BaseModel):
    """Retrieval step metrics."""
    latency_ms: float
    chunks_count: int = 0


class GenerationMetrics(BaseModel):
    """LLM generation step metrics."""
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0


class StepsDetail(BaseModel):
    """Detailed step-by-step pipeline metrics."""
    embedding: EmbeddingMetrics
    retrieval: RetrievalMetrics
    generation: GenerationMetrics


class SearchResponse(BaseModel):
    """Response from POST /playground/search."""
    query: str
    chunks: List[ChunkResult]
    steps: StepsDetail
    total_latency_ms: float


class ChatSource(BaseModel):
    """Source citation in chat response."""
    document_id: str
    filename: str
    chunk_id: str
    similarity: float
    page: Optional[int] = None


class ChatResponse(BaseModel):
    """Response from POST /playground/chat."""
    response: str
    chunks: List[ChunkResult]
    sources: List[ChatSource]
    steps: StepsDetail
    model: str
    total_latency_ms: float


class DocumentInfo(BaseModel):
    """Document listing item."""
    id: str
    filename: str
    format: str
    status: str
    chunk_count: int


class DocumentsResponse(BaseModel):
    """Response from GET /playground/documents."""
    documents: List[DocumentInfo]
    total: int
