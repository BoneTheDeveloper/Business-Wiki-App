# Phase 1: Backend Playground Endpoints

**Priority:** High
**Status:** ⏳ Pending
**Effort:** 0.5 day

## Context Links

- RAG service: `backend/app/services/rag_service.py`
- LLM service: `backend/app/services/llm_service.py`
- Chat route: `backend/app/api/v1/routes/chat.py`
- Search route: `backend/app/api/v1/routes/search.py`
- Schemas: `backend/app/schemas/search.py`
- Config: `backend/app/config.py`
- Main app: `backend/app/main.py`

## Overview

Add 3 new playground endpoints that wrap existing RAG services but return detailed step-by-step observability data (chunks, scores, latencies). Gated by `PLAYGROUND_ENABLED` env var, no JWT auth.

## Requirements

### Functional
- `POST /api/v1/playground/chat` — RAG chat with full step metadata
- `POST /api/v1/playground/search` — Semantic search with chunk details
- `GET /api/v1/playground/documents` — List all documents (no user filter)
- All endpoints return latency per step (embedding, retrieval, generation)
- Chat endpoint returns retrieved chunks with similarity scores

### Non-Functional
- Endpoints disabled unless `PLAYGROUND_ENABLED=true`
- No JWT auth required
- Returns structured JSON with step timing

## Architecture

### New Schema (`backend/app/schemas/playground.py`)

```python
class PlaygroundChatRequest(BaseModel):
    query: str = Field(min_length=3)
    top_k: int = 5
    document_ids: Optional[List[str]] = None

class ChunkDetail(BaseModel):
    chunk_id: str
    content: str
    similarity: float
    document_id: str
    filename: str
    page: Optional[int] = None
    chunk_index: int

class StepLatency(BaseModel):
    embedding_ms: float
    retrieval_ms: float
    generation_ms: float
    total_ms: float

class PlaygroundChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    chunks: List[ChunkDetail]
    steps: StepLatency
    model: str

class PlaygroundSearchRequest(BaseModel):
    query: str = Field(min_length=3)
    top_k: int = 10
    document_ids: Optional[List[str]] = None

class PlaygroundSearchResponse(BaseModel):
    query: str
    results: List[ChunkDetail]
    steps: StepLatency  # embedding_ms + retrieval_ms only
    total: int

class PlaygroundDocument(BaseModel):
    id: str
    filename: str
    format: Optional[str]
    status: str
    created_at: str
```

### Route File (`backend/app/api/v1/routes/playground.py`)

Key pattern: wrap rag_service calls with `time.perf_counter()` to measure each step.

```python
router = APIRouter(prefix="/playground", tags=["playground"])

# Dependency: check PLAYGROUND_ENABLED
async def require_playground_enabled():
    if not settings.PLAYGROUND_ENABLED:
        raise HTTPException(403, "Playground disabled")

@router.post("/chat", response_model=PlaygroundChatResponse)
async def playground_chat(
    request: PlaygroundChatRequest,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_playground_enabled)
):
    t0 = time.perf_counter()

    # Step 1: Embed query + retrieve chunks
    t1 = time.perf_counter()
    chunks = await rag_service.search(db, request.query, request.top_k, request.document_ids)
    t2 = time.perf_counter()

    # Step 2: Generate response
    llm_result = await llm_service.chat(request.query, chunks)
    t3 = time.perf_counter()

    # Build response with timing
    ...
```

### Config Addition (`backend/app/config.py`)

```python
PLAYGROUND_ENABLED: bool = False
```

### Registration (`backend/app/main.py`)

```python
from app.api.v1.routes.playground import router as playground_router
app.include_router(playground_router, prefix="/api/v1")
```

## Implementation Steps

1. Add `PLAYGROUND_ENABLED: bool = False` to `backend/app/config.py` Settings class
2. Create `backend/app/schemas/playground.py` with request/response models
3. Create `backend/app/api/v1/routes/playground.py` with 3 endpoints
4. Register playground router in `backend/app/main.py`
5. Test endpoints manually with curl

## Files to Create
- `backend/app/schemas/playground.py`
- `backend/app/api/v1/routes/playground.py`

## Files to Modify
- `backend/app/config.py` — Add PLAYGROUND_ENABLED
- `backend/app/main.py` — Register playground router

## Success Criteria
- `POST /api/v1/playground/chat` returns answer + chunks + step latencies
- `POST /api/v1/playground/search` returns chunks with scores + timing
- `GET /api/v1/playground/documents` lists all documents
- Endpoints return 403 when `PLAYGROUND_ENABLED=false`
- No auth token required when enabled

## Risk Assessment
| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Exposing all docs without auth | Medium | Only for local dev, gated by env var |
| Performance overhead from timing | Low | perf_counter is nanosecond-level |
| Breaking existing routes | Low | Separate router, no shared code changes |

## Next Steps
- Phase 2 depends on these endpoints being functional
- Chainlit app will consume these APIs
