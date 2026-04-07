---
name: Chainlit RAG Playground
description: Chainlit-based RAG playground for dev testing and stakeholder demos with full observability
status: complete
created: 2026-04-07
effort: 2-3 days
---

# Plan: Chainlit RAG Playground

## Overview

Create a Chainlit-based playground for testing and demoing the RAG pipeline. Runs as a separate Docker container, connects to backend via new playground API endpoints. Provides step-by-step pipeline visualization, retrieved chunks with similarity scores, and latency metrics.

## Architecture

```
Chainlit Container (:8001)     Backend Container (:8000)
┌──────────────────────┐       ┌──────────────────────────┐
│  chainlit app.py     │──HTTP─>│ /api/v1/playground/chat  │
│  ├─ Step UI          │       │ /api/v1/playground/search│
│  ├─ Chunk display    │<──────│ /api/v1/playground/docs  │
│  └─ Latency meters   │       └──────────────────────────┘
│                      │
│  No auth (local dev) │
│  PLAYGROUND_ENABLED  │
└──────────────────────┘
```

## Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | Backend playground endpoints | ✅ Done | 0.5 day |
| 2 | Chainlit app + UI | ✅ Done | 1 day |
| 3 | Docker config + integration | ✅ Done | 0.5 day |

## Key Files

### New Files
- `backend/app/api/v1/routes/playground.py` — Playground API endpoints
- `backend/app/schemas/playground.py` — Playground request/response schemas
- `chainlit/app.py` — Main Chainlit app
- `chainlit/api/client.py` — HTTP client for backend
- `chainlit/api/models.py` — Pydantic response models
- `chainlit/ui/steps.py` — RAG step builders
- `chainlit/ui/elements.py` — Custom elements (score tables, latency)
- `chainlit/Dockerfile` — Container definition
- `chainlit/pyproject.toml` — Dependencies
- `chainlit/config.yaml` — Chainlit config

### Modified Files
- `backend/app/main.py` — Register playground router
- `backend/app/config.py` — Add PLAYGROUND_ENABLED setting
- `docker/docker-compose.yml` — Add chainlit service

## Dependencies
- Backend RAG pipeline must be functional (rag_service, llm_service)
- Google Gemini API key configured
- Docker Compose running

## Security
- Playground endpoints gated by `PLAYGROUND_ENABLED=true` env var
- No JWT auth required for playground routes
- Only for local development — never enable in production

## References
- Brainstorm report: `plans/reports/brainstorm-260407-0911-chainlit-rag-playground.md`
- Research report: `plans/reports/researcher-260407-0918-chainlit-rag-playground.md`
- System architecture: `docs/architecture/system-architecture.md`
