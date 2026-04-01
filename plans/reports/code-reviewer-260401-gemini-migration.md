# Code Review: OpenAI to Google Gemini API Migration

**Date:** 2026-04-01
**Reviewer:** code-reviewer agent
**Scope:** 10 files changed across backend services, config, Docker, models, env files
**Focus:** SDK correctness, error handling, leftover OpenAI refs, security, compatibility

---

## Scope

- `backend/app/config.py` -- config key swap
- `backend/pyproject.toml` -- dependency swap
- `backend/app/services/rag_service.py` -- full rewrite (178 LOC)
- `backend/app/services/llm_service.py` -- full rewrite (117 LOC)
- `backend/app/services/celery_tasks.py` -- key reference swap (2 loc)
- `docker/docker-compose.yml` -- env var swap (2 services)
- `backend/.env.example` -- updated
- `.env.example` (root) -- updated
- `backend/app/models/document.py` -- comment update
- `backend/app/models/user.py` -- added social_accounts relationship
- **Consumers reviewed:** `chat.py`, `search.py`, `conftest.py`, `__init__.py`, `dependencies.py`

## Overall Assessment

Migration is well-executed. Core SDK usage is correct -- lazy `genai.Client` init, proper `aio.models.embed_content` / `aio.models.generate_content` calls, L2 normalization for cosine compatibility. The design decisions (keep 1536 dims, batch cap at 100, singleton pattern) are sound. Main gaps: missing try/catch around Gemini API calls, stale docs/env files, and a SQL param reuse issue.

---

## Critical Issues

### C1. No error handling on Gemini API calls in rag_service.py and llm_service.py

**Impact:** Unhandled `google.genai.errors` propagate as raw 500s. Rate limits, quota exhaustion, invalid key, network timeouts all crash the request with opaque stack traces.

**Affected:**
- `rag_service.py:71-78` -- `embed()` has no try/except
- `rag_service.py:94-100` -- `embed_batch()` has no try/except per batch
- `llm_service.py:82-90` -- `chat()` has no try/except on `generate_content`

**Recommendation:** Wrap each API call with specific error handling:
```python
from google.genai import errors as genai_errors

try:
    result = await self.client.aio.models.embed_content(...)
except genai_errors.ClientError as e:
    if e.status == 429:
        raise HTTPException(status_code=429, detail="Embedding rate limit hit")
    raise HTTPException(status_code=502, detail=f"Embedding service error: {e.message}")
except Exception as e:
    raise HTTPException(status_code=500, detail="Failed to generate embeddings")
```

### C2. Duplicate `:embedding` parameter in SQL query (rag_service.py:156)

**Impact:** SQLAlchemy `text()` binds `:embedding` once but it appears twice in the query (SELECT and ORDER BY). Most DBAPIs handle this fine, but `asyncpg` parameterized queries pass params positionally. If asyncpg resolves `:embedding` to two separate positional args, the second reference may get wrong binding or error.

**Line 133:** `1 - (dc.embedding <=> :embedding::vector) as similarity`
**Line 156:** `ORDER BY dc.embedding <=> :embedding::vector LIMIT :limit`

**Recommendation:** Test against live asyncpg. If it works, add a comment explaining the dual-use. If it fails, compute similarity in the ORDER BY clause from the alias:
```sql
ORDER BY similarity DESC LIMIT :limit
```
This avoids computing the distance twice and eliminates the duplicate param.

---

## High Priority

### H1. `.env` file still has OPENAI_API_KEY (stale)

**File:** `backend/.env` lines 32-33 and root `.env` lines 21-22 still contain:
```
# --- OpenAI ---
OPENAI_API_KEY=
```
Neither file was cleaned up. The `.env` files are gitignored but this causes confusion for developers. The `config.py` no longer reads `OPENAI_API_KEY`, so it's dead config.

**Recommendation:** Remove the OpenAI section from both `.env` files and add `GOOGLE_API_KEY=` entries.

### H2. Documentation completely stale -- every doc still references OpenAI

**Affected files (not exhaustive):**
- `docs/system-architecture.md` -- lines 96, 120, 244, 248, 263, 357, 507
- `docs/tech-stack.md` -- lines 64, 86, 88, 128, 183-186, 207, 227
- `docs/deployment-guide.md` -- lines 25, 68-69, 271, 309, 581-582
- `docs/project-overview-pdr.md` -- lines 136, 149, 264, 276, 293
- `docs/code-standards.md` -- lines 55, 223, 610
- `docs/codebase-summary.md` -- lines 31, 148-149, 178, 321, 352-353, 488, 493
- `docs/project-roadmap.md` -- lines 84, 92, 134, 325, 388, 435, 485
- `docs/diagrams/` -- all flow/architecture diagrams reference "OpenAI API"
- `README.md` -- lines 21, 26, 41, 80-81
- `supabase/config.toml` -- line 89: `openai_api_key = "env(OPENAI_API_KEY)"`

**Impact:** New developers following docs will be misled. Deployment guide will fail.

**Recommendation:** Bulk-update all docs as a follow-up task. The `supabase/config.toml` line is cosmetic (Supabase Studio AI feature, not your app), but should be updated for consistency.

### H3. `response.text` may be None or raise in llm_service.py:105

**Line:** `response.text or "I couldn't generate a response."`

The `google-genai` SDK's `response.text` is a property that raises `ValueError` when `candidates` is empty or when `finish_reason` is not `STOP`. This happens on safety blocks, empty responses, or recitation filters.

**Recommendation:**
```python
try:
    answer = response.text
except ValueError:
    answer = None
return {"answer": answer or "I couldn't generate a response.", ...}
```

### H4. `response.usage_metadata` fields may be None in llm_service.py:109-110

**Lines:**
```python
"prompt_tokens": response.usage_metadata.prompt_token_count or 0,
"completion_tokens": response.usage_metadata.candidates_token_count or 0
```

If `usage_metadata` itself is None (possible for some error/fallback responses), this raises `AttributeError`. Additionally, `prompt_token_count` could legitimately be `None`.

**Recommendation:**
```python
usage = response.usage_metadata
"prompt_tokens": getattr(usage, "prompt_token_count", 0) or 0,
"completion_tokens": getattr(usage, "candidates_token_count", 0) or 0,
```

---

## Medium Priority

### M1. Celery tasks silently skip embeddings when GOOGLE_API_KEY is empty

**Files:** `celery_tasks.py:85` and `celery_tasks.py:182`

The guard `if chunks and settings.GOOGLE_API_KEY:` means documents get marked `COMPLETED` with zero chunks if the key is missing. This is a silent data quality issue -- documents appear processed but have no embeddings, so search returns nothing.

**Recommendation:** When chunks exist but GOOGLE_API_KEY is missing, set status to `FAILED` with a descriptive error:
```python
if chunks and not settings.GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not configured; cannot generate embeddings")
```

### M2. `SocialAccount.access_token` stored in plaintext (pre-existing, not migration issue)

**File:** `backend/app/models/social_account.py:21`

OAuth access/refresh tokens stored as plaintext `String(500)`. Not introduced by this migration but noted for security completeness.

### M3. `embed_batch` lacks retry logic for partial failures

**File:** `rag_service.py:80-105`

If the 3rd batch of 5 fails, the first 2 batches' embeddings are lost because `all_embeddings` is built in-memory and the caller (celery_tasks.py) stores them transactionally. The whole operation fails and retries from scratch.

**Recommendation:** Low priority for MVP. Document that batch embedding is all-or-nothing. For production, consider persisting partial results.

### M4. Lazy client never refreshes when settings change at runtime

Both `rag_service.py` and `llm_service.py` create `genai.Client` once and cache it in `_client`. If `GOOGLE_API_KEY` is rotated (e.g., via hot reload), the stale client with the old key persists until process restart.

**Recommendation:** Acceptable for MVP. For production, add a `reset()` method or check key staleness.

### M5. `gemini_contents` built as plain dicts, not SDK types (llm_service.py:66-79)

The code builds `{"role": "user", "parts": [{"text": ...}]}` dicts. The `google-genai` SDK accepts both dicts and `types.Content` objects. Dicts work but lose type safety.

**Recommendation:** Low priority. Dicts are fine and arguably more readable for this use case.

---

## Low Priority

### L1. `datetime.utcnow` is deprecated in Python 3.12+ (pre-existing)

Used in `document.py`, `user.py`, `social_account.py`. Should use `datetime.now(datetime.UTC)`. Not migration-related.

### L2. `langchain-text-splitters` retained as only langchain dep

`pyproject.toml` correctly removed `langchain` and `langchain-openai` but kept `langchain-text-splitters`. This is correct (only `RecursiveCharacterTextSplitter` is used), but pulling in langsmith as a transitive dep. Consider extracting the splitting logic inline to drop the dependency entirely.

### L3. `numpy` added as a dependency for a single normalization operation

`_normalize()` uses `numpy` for one `linalg.norm` call. Could be a 3-line pure-Python function:
```python
norm = sum(x * x for x in values) ** 0.5
return [x / norm for x in values] if norm else values
```
But numpy is already pulled in by other deps and the array operation is idiomatic. Low priority.

---

## Edge Cases Found by Scout

| # | Edge Case | Risk | Location |
|---|-----------|------|----------|
| 1 | Gemini safety block causes `response.text` to raise `ValueError` | High | `llm_service.py:105` |
| 2 | `usage_metadata` is None on blocked/error responses | High | `llm_service.py:109-110` |
| 3 | Duplicate `:embedding` param binding in SQL | Medium | `rag_service.py:133,156` |
| 4 | Documents marked COMPLETED with zero chunks when key missing | Medium | `celery_tasks.py:85,105` |
| 5 | Empty batch after filtering passes `[]` to embed -- handled (line 86) | None | `rag_service.py:85-86` |
| 6 | `_normalize` on zero vector returns original unnormalized vector | Low | `rag_service.py:62-63` |
| 7 | Celery worker in Docker missing `SUPABASE_URL` and `SUPABASE_*_KEY` env vars | Low | `docker-compose.yml:66-72` |
| 8 | `embed_batch` called with mismatched chunks/embeddings if API returns fewer results than inputs | Medium | `celery_tasks.py:91` |

---

## Positive Observations

1. **Lazy init pattern** -- correct solution for `genai.Client` crashing on empty key. Clean `@property` approach.
2. **L2 normalization** -- well-considered. Gemini embeddings are not unit-normalized by default; applying L2 norm makes pgvector cosine distance (`<=>`) mathematically correct.
3. **Clean dependency swap** -- `pyproject.toml` is minimal, no orphaned deps.
4. **Singleton pattern preserved** -- no unnecessary object creation per request.
5. **Batch cap at 100** -- defensive but reasonable for Gemini's limits.
6. **`system_instruction` via config** -- correct Gemini pattern, separates system prompt from user contents.
7. **No OpenAI references in `backend/app/` source code** -- clean cut.
8. **`social_accounts` relationship** -- correct fix for the pre-existing missing back-reference.

---

## Recommended Actions

1. **[Critical]** Add try/except around all Gemini API calls in `rag_service.py` and `llm_service.py` -- handle rate limits, auth errors, network failures
2. **[Critical]** Verify duplicate `:embedding` param works with asyncpg, or refactor to ORDER BY similarity alias
3. **[High]** Wrap `response.text` access in `llm_service.py` to handle `ValueError` from safety blocks
4. **[High]** Add None-safety for `response.usage_metadata` in `llm_service.py`
5. **[High]** Clean `.env` files -- remove stale OPENAI sections, add GOOGLE_API_KEY
6. **[High]** Update all docs (system-architecture, tech-stack, deployment-guide, README, diagrams) to reflect Gemini
7. **[Medium]** Fail document processing with clear error when GOOGLE_API_KEY is missing instead of silently creating zero-chunk documents
8. **[Medium]** Verify Celery worker docker-compose has all required env vars (SUPABASE_URL/keys appear missing)

---

## Metrics

| Metric | Value |
|--------|-------|
| Files changed | 10 |
| LOC reviewed | ~550 |
| OpenAI refs in source | 0 (clean) |
| OpenAI refs in docs | ~50+ (stale) |
| OpenAI refs in .env files | 2 (stale) |
| Test coverage for Gemini code | 0 (no unit tests for rag/llm services) |
| Type checking | N/A (no mypy/pyright configured) |

---

## Unresolved Questions

1. **Re-indexing strategy:** Plan mentions all documents need re-embedding after migration (OpenAI vectors incompatible with Gemini vectors). Is there a migration script or manual re-index step documented?
2. **Celery worker Docker config:** Missing `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` in celery_worker environment. Is this intentional (Celery only needs DB + Redis + MinIO)?
3. **`supabase/config.toml` line 89:** The `openai_api_key = "env(OPENAI_API_KEY)"` is for Supabase Studio AI, not your app. Leave as-is or update?
4. **Embedding dimension mismatch risk:** If someone later changes `embed_dimensions` from 1536 to another value, existing pgvector data becomes invalid. Should this be a migration-guarded constant?
5. **gemini-2.0-flash model availability:** Is `gemini-2.0-flash` the correct stable model identifier? Some regions/projects may only have `gemini-1.5-flash`. Worth verifying.
