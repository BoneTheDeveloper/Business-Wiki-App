# Brainstorm: Chainlit RAG Playground

**Date:** 2026-04-07
**Status:** Agreed — Ready for planning

## Problem Statement

Need a Chainlit-based playground for implementing and testing the RAG flow. Serves dual purpose: developer testing + stakeholder demos. Runs as a separate Docker container connecting to existing backend API.

## Requirements

| Requirement | Priority |
|---|---|
| Retrieved chunks display with similarity scores | Must |
| Step-by-step pipeline visualization (Query → Embed → Retrieve → Context → LLM) | Must |
| Latency & metrics per query (retrieval, LLM, total) | Must |
| Settings sidebar for parameter tuning (top-k, temperature) | Future |
| No auth (local dev only) | Must |
| Separate Docker container | Must |

## Architecture Decision: Hybrid Approach

```
Chainlit Container              Backend Container
┌──────────────────────┐       ┌──────────────────────────┐
│  chainlit app.py     │──HTTP─>│ /api/v1/chat             │
│                      │       │ /api/v1/search           │
│  Step UI:            │       │ /api/v1/playground/*  ←NEW│
│  ├─ Retrieval step   │<──────│  debug/retrieval results  │
│  ├─ Embedding step   │       │  chunk details + scores   │
│  └─ Generation step  │       │  latency metrics          │
│                      │       └──────────────────────────┘
│  Sidebar:            │
│  ├─ Latency meters   │
│  └─ Score table      │
│                      │
│  No auth (local dev) │
└──────────────────────┘
```

**Why Hybrid over alternatives:**
- **API-only** → can't see intermediate RAG steps (backend doesn't expose them)
- **Standalone** → code duplication, doesn't test real API
- **Hybrid** → best of both: tests real API + full observability via debug endpoints

## New Backend Endpoints (Playground API)

New route group `/api/v1/playground/` with auth bypass for local dev:

```
POST /api/v1/playground/chat     # Chat with detailed RAG step info
POST /api/v1/playground/search   # Search with chunk details
GET  /api/v1/playground/documents # List available docs (no auth)
```

Response format for `/playground/chat`:
```json
{
  "response": "...",
  "steps": {
    "embedding": { "latency_ms": 120, "dimensions": 1536 },
    "retrieval": { "latency_ms": 45, "chunks_count": 10 },
    "generation": { "latency_ms": 1500, "tokens_used": 850 }
  },
  "chunks": [
    { "content": "...", "score": 0.92, "source": "doc.pdf", "page": 3 }
  ],
  "total_latency_ms": 1665
}
```

## Docker Integration

Add to existing `docker/docker-compose.yml`:

```yaml
chainlit:
  build:
    context: ../chainlit
    dockerfile: Dockerfile
  ports:
    - "${CHAINLIT_PORT:-8001}:8000"
  environment:
    BACKEND_URL: http://backend:8000
    GOOGLE_API_KEY: ${GOOGLE_API_KEY:-}
  depends_on:
    - backend
```

## Chainlit Project Structure

```
chainlit/
├── Dockerfile
├── pyproject.toml          # deps: chainlit, httpx, google-genai
├── app.py                  # Main Chainlit app
├── config.yaml             # Chainlit config (no auth, port)
├── api/
│   ├── client.py           # HTTP client for backend API
│   └── models.py           # Pydantic models for API responses
├── ui/
│   ├── steps.py            # Step builders (retrieval, embedding, generation)
│   └── elements.py         # Custom elements (score tables, latency meters)
└── .env.example
```

## V1 Scope (Must-Haves)

1. **Chat with RAG steps** — sends query to playground API, renders each step
2. **Retrieved chunks display** — sidebar shows chunks with scores, source, page
3. **Latency metrics** — per-step timing displayed inline
4. **Docker container** — standalone container in docker-compose
5. **No auth** — config.yaml `auth_enabled: false`

## V2 Scope (Future)

- Settings sidebar (top-k slider, temperature, chunk size)
- A/B testing of RAG parameters
- Export conversation as report
- Multi-user support

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Backend debug endpoints expose data without auth | Medium | Only enable playground routes when `PLAYGROUND_ENABLED=true` env var set |
| Chainlit version compatibility | Low | Pin version in pyproject.toml |
| Docker networking issues | Low | Same docker-compose network, use service names |

## Effort Estimate

| Component | LOC | Effort |
|---|---|---|
| Backend playground endpoints | ~150 | 0.5 day |
| Chainlit app + UI | ~250 | 1 day |
| Docker config | ~30 | 0.5 day |
| Testing & integration | ~100 | 0.5 day |
| **Total** | **~530** | **2-3 days** |

## Next Steps

1. Create implementation plan via `/ck:plan`
2. Update system-architecture.md and roadmap
3. Implement backend playground endpoints
4. Implement Chainlit app
5. Add Docker config

## Unresolved Questions

- Should playground endpoints use same CORS policy as main API?
- Should Chainlit container have direct DB access for future features?
