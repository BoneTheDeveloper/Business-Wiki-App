# Phase 2: Chainlit App + UI

**PRIORITY:** High
**STATUS:** ⏳ Pending
**EFFORT:** 1 day

## Context Links

- Chainlit docs: https://docs.chainlit.io/
- Research report: `plans/reports/researcher-260407-0918-chainlit-rag-playground.md`
- Backend playground endpoints: `backend/app/api/v1/routes/playground.py` (Phase 1)

## Overview

Create the Chainlit application with step-by-step RAG pipeline visualization, chunk display, and latency metrics. Connects to backend via HTTP.

## Requirements

### Functional
- Chat interface with RAG step visualization
- Each query shows: Embedding → Retrieval → Context Assembly → Generation steps
- Retrieved chunks displayed in sidebar with similarity scores, source doc, page
- Latency metrics per step shown inline
- Document selector to filter which documents to query against

### Non-Functional
- Async HTTP client (httpx) for backend calls
- Type-safe response models (Pydantic)
- Clean error handling with user-friendly messages
- No auth (local dev)

## Architecture

### Project Structure
```
chainlit/
├── app.py                  # Main Chainlit app (on_message, on_start)
├── config.yaml             # Chainlit config (no auth, port 8000)
├── pyproject.toml          # Python deps (chainlit, httpx, pydantic)
├── api/
│   ├── client.py           # Async HTTP client for backend
│   └── models.py           # Response models matching backend schemas
├── ui/
│   ├── steps.py            # RAG step builders (embedding, retrieval, generation)
│   └── elements.py         # Custom elements (chunk cards, score tables, latency)
└── .env.example            # BACKEND_URL
```

### Key Components

**app.py** — Main entry:
- `@cl.on_chat_start` — Welcome message, show available docs
- `@cl.on_message` — Process query: call playground/chat, render steps, show chunks
- Uses `cl.Step` for pipeline visualization
- Uses `cl.Text` elements for chunk display

**api/client.py** — Backend HTTP client:
- `AsyncClient` from httpx
- `playground_chat(query, top_k, doc_ids)` → calls POST /playground/chat
- `playground_search(query, top_k)` → calls POST /playground/search
- `list_documents()` → calls GET /playground/documents
- Base URL from `BACKEND_URL` env var

**api/models.py** — Response models:
- `PlaygroundChatResponse` — answer, chunks, steps, total_latency
- `PlaygroundSearchResponse` — results with scores, timing
- `DocumentInfo` — id, filename, status, chunk_count
- `ChunkInfo` — content, score, source, page
- `StepMetrics` — step_name, latency_ms, details

**ui/steps.py** — Step builders:
- `render_embedding_step(metrics)` — shows embedding latency + dimensions
- `render_retrieval_step(metrics, chunks)` — shows retrieval latency + chunk count
- `render_generation_step(metrics, tokens)` — shows generation latency + token usage

**ui/elements.py** — Custom elements:
- `create_chunk_element(chunk)` — cl.Text with score, source, content
- `create_latency_table(steps)` — cl.Text with formatted latency summary

### Data Flow

```
User message → app.py on_message
  → api/client.py playground_chat(query)
    → POST http://backend:8000/api/v1/playground/chat
    ← JSON: { answer, chunks[], steps{}, total_latency_ms }
  → ui/steps.py: render each step with cl.Step
  → ui/elements.py: create chunk elements with cl.Text
  → cl.Message(content=answer, elements=[chunks]).send()
```

## Related Code Files

### Files to Create
- `chainlit/app.py`
- `chainlit/config.yaml`
- `chainlit/pyproject.toml`
- `chainlit/api/client.py`
- `chainlit/api/models.py`
- `chainlit/ui/steps.py`
- `chainlit/ui/elements.py`
- `chainlit/.env.example`

### Files to Read (context)
- `backend/app/api/v1/routes/playground.py` (Phase 1 output)
- `backend/app/schemas/search.py` — existing schema shapes

## Implementation Steps

1. Initialize chainlit project: pyproject.toml with deps
2. Create config.yaml (auth_enabled: false, port: 8000)
3. Create api/models.py — response Pydantic models
4. Create api/client.py — httpx async client
5. Create ui/steps.py — step rendering functions
6. Create ui/elements.py — chunk/latency elements
7. Create app.py — main Chainlit handlers
8. Create .env.example
9. Test locally: `chainlit run app.py`

## Success Criteria
- Chat query shows all RAG steps with timing
- Retrieved chunks displayed with similarity scores and source
- Latency summary shown after each query
- Error messages shown for backend failures
- `chainlit run app.py` starts successfully

## Risk Assessment
| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Chainlit version compatibility | Low | Pin version in pyproject.toml |
| Backend not reachable from container | Medium | Use service name `backend` in Docker |
| Large chunk responses slow UI | Low | Limit display to top-10 chunks |

## Next Steps
- Phase 3 wraps this in Docker + adds to docker-compose
