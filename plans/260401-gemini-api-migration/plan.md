---
title: "Migrate from OpenAI API to Google Gemini API"
description: "Replace OpenAI SDK with google-genai for embeddings and chat across the entire backend"
status: pending
priority: P1
effort: 3h
branch: main
tags: [migration, gemini, embeddings, llm, rag]
created: 2026-04-01
---

## Overview

Migrate the RAG Business Wiki App from OpenAI API to Google Gemini API for both embeddings and chat completions. No DB schema change -- keep `Vector(1536)` with L2 normalization on Gemini embeddings.

## Phases

| Phase | File | Status | Effort |
|-------|------|--------|--------|
| [Phase 1](phase-01-config-and-dependencies.md) | Config + Dependencies | pending | 30m |
| [Phase 2](phase-02-rag-service.md) | RAG Service | pending | 45m |
| [Phase 3](phase-03-llm-service.md) | LLM Service | pending | 30m |
| [Phase 4](phase-04-celery-and-docker.md) | Celery Tasks + Docker | pending | 20m |
| [Phase 5](phase-05-tests-and-verification.md) | Tests + Verification | pending | 30m |

## Key Decisions

- **1536 dims, no DB migration** -- `gemini-embedding-001` with `output_dimensionality=1536`
- **L2 normalization required** -- Gemini non-3072 dims need normalization for cosine similarity accuracy
- **`google-genai` SDK** (not `google-generativeai`) -- newer, cleaner API
- **Remove** `openai`, `langchain-openai` deps; keep `langchain-text-splitters`
- **No existing vector data loss** -- all existing embeddings invalid after migration; documents need re-indexing

## Critical Risk

**Existing embeddings are OpenAI vectors. After migration, cosine similarity between old (OpenAI) and new (Gemini) vectors is meaningless.** All documents must be re-indexed post-migration. Plan includes a re-index strategy.

## Dependency Graph

```
Phase 1 (config/deps) --> Phase 2 (rag_service)
                       --> Phase 3 (llm_service)
                       --> Phase 4 (celery/docker)
Phase 2 + 3 + 4      --> Phase 5 (tests/verify)
```

## Files Modified

| File | Change |
|------|--------|
| `backend/app/config.py` | Add `GOOGLE_API_KEY`, deprecate `OPENAI_API_KEY` |
| `backend/app/services/rag_service.py` | Replace AsyncOpenAI with genai.Client + normalization |
| `backend/app/services/llm_service.py` | Replace AsyncOpenAI with genai.Client |
| `backend/app/services/celery_tasks.py` | `OPENAI_API_KEY` -> `GOOGLE_API_KEY` |
| `backend/pyproject.toml` | Swap deps: `openai` -> `google-genai`, remove `langchain-openai` |
| `backend/.env.example` | Add `GOOGLE_API_KEY` |
| `.env.example` (root) | Add `GOOGLE_API_KEY` |
| `docker/docker-compose.yml` | `OPENAI_API_KEY` -> `GOOGLE_API_KEY` |
| `backend/app/models/document.py` | Update comment on Vector column |

## Post-Migration Steps

1. Set `GOOGLE_API_KEY` in all `.env` files
2. Run `uv sync` to install new deps
3. Re-index all existing documents (old embeddings are invalid)
