---
title: "Phase 5: Tests & Verification"
description: "Run existing tests, verify no OpenAI references remain, validate Gemini integration"
status: pending
priority: P1
effort: 30m
phase: 5
---

## Context Links
- [Plan Overview](plan.md)
- Test files: `backend/tests/test_search.py`, `backend/tests/test_chat.py`, `backend/tests/test_documents.py`
- Test config: `backend/tests/conftest.py`

## Overview

Run the existing test suite to verify nothing broke. Perform a final grep sweep for any remaining OpenAI references. Optionally test Gemini API calls with a real key.

## Requirements

### Functional
- All existing tests pass
- Zero `openai` / `OPENAI` references in `backend/app/` source (not venv, not uv.lock)
- Gemini SDK imports and instantiates correctly

## Implementation Steps

### 1. Grep Sweep for Remaining OpenAI References
```bash
# Check backend source (excluding .venv, uv.lock)
grep -rn "openai\|OPENAI" backend/app/ --include="*.py"
grep -rn "openai\|OPENAI" docker/
grep -rn "openai\|OPENAI" backend/.env.example
grep -rn "openai\|OPENAI" .env.example
```
Expected: zero matches in all paths.

### 2. Verify Python Imports
```bash
cd backend
uv run python -c "
from google import genai
from google.genai import types
from app.config import settings
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service
print('All imports OK')
print(f'Config has GOOGLE_API_KEY: {hasattr(settings, \"GOOGLE_API_KEY\")}')
print(f'RAGService model: {rag_service.embed_model}')
print(f'LLMService model: {llm_service.model}')
"
```

### 3. Run Existing Tests
```bash
cd backend
uv run pytest tests/ -v
```

Tests use SQLite (no pgvector) so vector operations will fail -- this is expected for embedding-related tests. The existing tests in `test_search.py`, `test_chat.py`, `test_documents.py` test API endpoints with mocked dependencies, so they should pass if imports are clean.

### 4. Verify Embedding Normalization (manual smoke test if API key available)
```bash
cd backend
uv run python -c "
import asyncio, numpy as np
from app.services.rag_service import rag_service

async def test():
    emb = await rag_service.embed('test query')
    norm = np.linalg.norm(np.array(emb))
    print(f'Dimensions: {len(emb)}')
    print(f'L2 norm: {norm:.6f}')
    assert abs(norm - 1.0) < 1e-6, f'Not normalized! norm={norm}'
    print('Normalization OK')

asyncio.run(test())
"
```

### 5. Verify Chat Generation (manual smoke test if API key available)
```bash
cd backend
uv run python -c "
import asyncio
from app.services.llm_service import llm_service

async def test():
    result = await llm_service.chat('What is Python?', [])
    print(f'Model: {result[\"model\"]}')
    print(f'Answer: {result[\"answer\"][:100]}...')
    print(f'Usage: {result[\"usage\"]}')

asyncio.run(test())
"
```

### 6. Re-index Strategy for Existing Documents
After migration, all existing embeddings are invalid (OpenAI vectors incompatible with Gemini vectors). Options:
- **Option A (Recommended):** Trigger `reindex_document_task` for all completed documents via admin endpoint or script
- **Option B:** Delete all `document_chunks` rows and re-process documents

Document the re-index step as a post-deploy task.

## Todo List
- [ ] Grep sweep -- zero OpenAI references in `backend/app/`
- [ ] Grep sweep -- zero OpenAI references in `docker/` and `.env.example` files
- [ ] Verify Python imports all succeed
- [ ] Run `uv run pytest tests/ -v` -- all pass
- [ ] (Optional) Smoke test embedding with real API key
- [ ] (Optional) Smoke test chat with real API key
- [ ] Document re-index step for existing documents

## Success Criteria
- All existing tests pass
- Zero OpenAI references in source code
- Gemini imports work, config has `GOOGLE_API_KEY`
- (If API key available) Embedding returns 1536-dim unit vector
- (If API key available) Chat returns non-empty answer

## Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| SQLite tests fail due to missing Vector type | Medium | Tests should mock DB; existing tests use SQLite which lacks pgvector -- check if conftest handles this |
| Rate limiting on Gemini API during smoke tests | Low | Single request tests, not load |
| Existing documents have stale embeddings | High | Document re-index requirement clearly; plan to bulk-reindex post-deploy |

## Unresolved Questions
- Should we build a dedicated re-index CLI command (e.g., `uv run python -m app.cli reindex-all`)?
- Is there an admin API endpoint that already supports bulk re-index?
