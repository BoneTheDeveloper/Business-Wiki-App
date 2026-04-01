---
title: "Phase 1: Config & Dependencies"
description: "Update settings, pyproject.toml, and env files for Gemini"
status: pending
priority: P1
effort: 30m
phase: 1
---

## Context Links
- [Plan Overview](plan.md)
- Current config: `backend/app/config.py`
- Current deps: `backend/pyproject.toml`

## Overview

Swap OpenAI dependency for Google Gemini SDK. Add `GOOGLE_API_KEY` to settings. Update all env files.

## Requirements

### Functional
- `Settings` class exposes `GOOGLE_API_KEY`
- `OPENAI_API_KEY` removed from config (no backward compat needed -- clean break)
- `pyproject.toml` replaces `openai` with `google-genai>=1.0.0`
- `langchain-openai` removed (only `langchain-text-splitters` kept)

### Non-Functional
- No breaking change to DB schema or API surface

## Architecture

```
config.py:  GOOGLE_API_KEY (str, default="")
              ↓
rag_service.py / llm_service.py read settings.GOOGLE_API_KEY
              ↓
genai.Client(api_key=settings.GOOGLE_API_KEY)
```

## Related Code Files

### Modify
- `backend/app/config.py` -- Replace `OPENAI_API_KEY` with `GOOGLE_API_KEY`
- `backend/pyproject.toml` -- Swap deps

### Modify (env/config files)
- `backend/.env.example` -- Replace `OPENAI_API_KEY` with `GOOGLE_API_KEY`
- `.env.example` (root) -- Replace `OPENAI_API_KEY` with `GOOGLE_API_KEY`
- `backend/app/models/document.py` -- Update comment on line 57

## Implementation Steps

1. **`backend/app/config.py`**
   - Remove `OPENAI_API_KEY: str = ""`
   - Add `GOOGLE_API_KEY: str = ""`
   - Update section comment from `# OpenAI` to `# Google Gemini`

2. **`backend/pyproject.toml`**
   - Remove `"openai>=1.68.0"`
   - Remove `"langchain-openai>=0.3.0"`
   - Remove `"langchain>=0.3.0"` (only used as transitive dep for langchain-openai)
   - Add `"google-genai>=1.0.0"`
   - Keep `"langchain-text-splitters>=0.3.0"` (used by rag_service)

3. **`backend/.env.example`**
   - Replace `# --- OpenAI (RAG: embeddings + chat) ---` section
   - Replace `OPENAI_API_KEY=sk-your-openai-api-key` with `GOOGLE_API_KEY=your-google-api-key`

4. **Root `.env.example`**
   - Replace `# --- OpenAI (passed to backend + celery containers) ---` section
   - Replace `OPENAI_API_KEY=sk-your-openai-api-key` with `GOOGLE_API_KEY=your-google-api-key`

5. **`backend/app/models/document.py`** line 57
   - Change comment: `# OpenAI text-embedding-3-small dimensions` -> `# Gemini embedding dimensions (1536)`

6. **Run `uv sync`** to verify new deps resolve

## Todo List
- [ ] Update `backend/app/config.py` -- replace API key field
- [ ] Update `backend/pyproject.toml` -- swap dependencies
- [ ] Update `backend/.env.example` -- new env var
- [ ] Update root `.env.example` -- new env var
- [ ] Update `backend/app/models/document.py` -- comment
- [ ] Run `uv sync` -- verify lock file updates
- [ ] Run `uv run python -c "from google import genai; print('OK')"` -- verify import

## Success Criteria
- `uv sync` completes without errors
- `from google import genai` imports successfully
- No remaining references to `openai` in source code (except uv.lock)
- `GOOGLE_API_KEY` present in all .env.example files

## Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| `google-genai` version incompatibility | High | Pin minimum 1.0.0, test import immediately |
| `langchain-text-splitters` breaks without `langchain` core | Medium | It depends on `langchain-core` which installs automatically; verify after sync |

## Next Steps
- Unblocks Phase 2 (rag_service), Phase 3 (llm_service), Phase 4 (celery/docker)
