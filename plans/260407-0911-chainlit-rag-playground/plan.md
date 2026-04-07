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

## Completion Notes
All phases completed successfully:

**Phase 1 - Backend playground endpoints:**
- Created `backend/app/api/v1/routes/playground.py` with 3 endpoints (chat, search, documents)
- Fixed duplicate embedding call - routes now use raw SQL with pgvector instead of calling rag_service.search
- Added query validation (min 3 chars) to search endpoint
- Created `backend/app/schemas/playground.py` with all request/response models
- Added `PLAYGROUND_ENABLED: bool = False` to `backend/app/config.py`
- Registered playground router in `backend/app/main.py`

**Phase 2 - Chainlit app + UI:**
- Created `chainlit/app.py` with step-by-step RAG pipeline visualization
- Fixed syntax errors in app.py and elements.py (bad indentation)
- Created `chainlit/api/client.py` with httpx async client for backend calls
- Created `chainlit/api/models.py` with Pydantic response models
- Created `chainlit/ui/steps.py` with RAG step builders
- Created `chainlit/ui/elements.py` with chunk display and latency metrics
- Created `chainlit/config.yaml` (removed incorrect [project] header)
- Created `chainlit/pyproject.toml` with dependencies

**Phase 3 - Docker config + integration:**
- Fixed Dockerfile (pip install . instead of pip install -r pyproject.toml)
- Added chainlit service to `docker/docker-compose.yml` with `profiles: [playground]`
- Added `CHAINLIT_PORT=8001` to root `.env.example`
- Added `PLAYGROUND_ENABLED=false` to backend `.env.example`
- Added `PLAYGROUND_ENABLED=${PLAYGROUND_ENABLED:-false}` to docker-compose.yml
- Created `chainlit/Dockerfile` and `.dockerignore`

**Fixes Applied:**
1. Removed duplicate embedding calls - playground routes do raw SQL with pgvector directly
2. Fixed syntax errors in chainlit files (app.py, elements.py)
3. Fixed Dockerfile (pip install . instead of pip install -r pyproject.toml)
4. Fixed chainlit config.toml (removed incorrect [project] header)
5. Added `PlaygroundDocumentInfo` to imports in app.py
6. Added `PLAYGROUND_ENABLED` to backend .env.example
7. Added `CHAINLIT_PORT` to root .env.example
8. Added chainlit service to docker-compose.yml with profiles: [playground]
9. Added query validation (min 3 chars) to search endpoint

## Security
- Playground endpoints gated by `PLAYGROUND_ENABLED=true` env var
- No JWT auth required for playground routes
- Only for local development — never enable in production

## References
- Brainstorm report: `plans/reports/brainstorm-260407-0911-chainlit-rag-playground.md`
- Research report: `plans/reports/researcher-260407-0918-chainlit-rag-playground.md`
- System architecture: `docs/architecture/system-architecture.md`
