# Code Review: Chainlit RAG Playground

**Reviewer:** code-reviewer
**Date:** 2026-04-07
**Scope:** Backend playground routes, Chainlit app, HTTP client, UI components, Docker config

## Scope

| File | LOC | Role |
|------|-----|------|
| `backend/app/api/v1/routes/playground.py` | 280 | Backend playground API (3 endpoints, no auth) |
| `backend/app/schemas/playground.py` | 100 | Pydantic request/response schemas |
| `chainlit/app.py` | 98 | Main Chainlit chat handler |
| `chainlit/api/client.py` | 54 | httpx async client to backend |
| `chainlit/api/models.py` | 83 | Pydantic models mirroring backend schemas |
| `chainlit/ui/steps.py` | 57 | Chainlit step builders |
| `chainlit/ui/elements.py` | 53 | Markdown table/sidebar element builders |
| `chainlit/Dockerfile` | 13 | Container config |
| `docker/docker-compose.yml` | 107 | Docker Compose with chainlit service |

**Focus:** Recent/specific (new Chainlit playground feature)
**Scout findings:** See edge cases section below.

---

## Overall Assessment

Clean implementation with good observability design. The SQL is parameterized, the env-gate pattern is consistent, and the code is well-structured with clear separation (api/ui/app). Main concerns are around the unguarded playground endpoints exposing all document content without any scoping, and a few resilience gaps in the Chainlit client layer.

---

## Critical Issues

### C1. [Security] Playground endpoints expose all user documents without ownership scoping
**Severity:** CRITICAL
**File:** `backend/app/api/v1/routes/playground.py` (lines 55-72, 131-148, 252-261)

All three playground endpoints (`/search`, `/chat`, `/documents`) return data from **every completed document in the database** with no user or organization filter. When `PLAYGROUND_ENABLED=true`, anyone with network access can read all document chunks, filenames, and content across all tenants.

The `/documents` endpoint (line 252-279) lists every document with chunk counts. The `/search` and `/chat` endpoints return full chunk content.

This is acknowledged as "local dev only" but the env-var gate is a single boolean. A misconfigured deployment or leaked `PLAYGROUND_ENABLED=true` in production exposes everything.

**Risk:** Data breach if playground is accidentally enabled in a deployed environment. No defense-in-depth -- no IP allowlist, no network isolation requirement, no warning log at startup.

### C2. [Security] Error message in Chainlit leaks backend error details to end user
**Severity:** HIGH
**File:** `chainlit/app.py` (line 95-97)

```python
except Exception as e:
    error_text = str(e)[:300]
    await cl.Message(content=f"**Error:** {error_text}").send()
```

Catches all exceptions and forwards the raw error text (up to 300 chars) directly to the chat UI. This can include backend stack traces, database error messages, internal URLs, or connection string fragments from httpx/SQLAlchemy errors. The httpx `raise_for_status()` on the client side produces error bodies that may contain internal routing details.

**Risk:** Information disclosure -- internal infrastructure details leaked to whoever has access to the Chainlit UI.

---

## High Priority Issues

### H1. [Performance] New httpx.AsyncClient created per request (no connection pooling)
**Severity:** HIGH
**File:** `chainlit/api/client.py` (lines 24, 42, 50)

Every call to `search()`, `chat()`, and `list_documents()` creates a fresh `httpx.AsyncClient` via `async with`. This means:
- TCP handshake + TLS negotiation on every request
- No HTTP/2 multiplexing or keep-alive benefit
- Under concurrent load, connection churn wastes resources

The Chainlit app calls `list_documents()` on session start, then `chat()` on every message. For active users, this is a significant overhead.

**Recommendation:** Create a module-level or session-scoped client instance.

### H2. [Resilience] Chainlit client does not handle non-JSON error responses
**Severity:** HIGH
**File:** `chainlit/api/client.py` (lines 26-27, 44-45, 52-53)

Pattern: `resp.raise_for_status()` followed by `resp.json()`. If `raise_for_status()` raises (e.g., 403 when playground is disabled), the exception propagates unhandled with the raw httpx error. The caller in `app.py` catches it generically but shows the raw error to the user.

If the backend returns a 502/503 with an HTML body, `resp.json()` would fail with a JSON parse error, masking the real HTTP error.

**Recommendation:** Catch `httpx.HTTPStatusError` explicitly and extract the backend's `detail` field from the JSON error body.

### H3. [Bug] Inconsistent query validation between search and chat endpoints
**Severity:** HIGH
**File:** `backend/app/api/v1/routes/playground.py`

`/chat` validates minimum query length (line 121: `if len(request.query.strip()) < 3`), but `/search` has **no query validation at all**. An empty query would trigger an embedding API call that wastes resources and returns meaningless results.

Both endpoints also lack a maximum query length check. Extremely long queries could hit embedding API token limits or cause oversized SQL parameters.

### H4. [Security] No rate limiting on playground endpoints
**Severity:** HIGH
**File:** `backend/app/api/v1/routes/playground.py`

Each `/chat` call triggers: 1 embedding API call + 1 DB query + 1 LLM API call. Each `/search` call triggers: 1 embedding API call + 1 DB query. No rate limiting means:
- A single client can burn through Google API quotas
- DB load is unbounded
- No protection against automated scraping of all document chunks

---

## Medium Priority Issues

### M1. [Code Quality] Duplicated SQL query in search and chat endpoints
**Severity:** MEDIUM
**File:** `backend/app/api/v1/routes/playground.py` (lines 55-72 vs 131-148)

The vector search SQL is copy-pasted verbatim between `playground_search` and `playground_chat`. This is the exact same query already in `rag_service.search()` (lines 127-161 of `rag_service.py`). The comment says "skip re-embedding" but the duplication means three copies of the same SQL to maintain.

If the schema changes (e.g., adding soft-delete, or a new filter), all three locations must be updated.

### M2. [Resilience] Conversation history grows unbounded in Chainlit session
**Severity:** MEDIUM
**File:** `chainlit/app.py` (lines 53-56, 73-74)

Every message appends to `conversation_history` in `cl.user_session` with no truncation. Long sessions will send increasingly large payloads to the backend, which itself only keeps the last 4 messages (line 191-192 in playground.py). The full history is sent over the wire but only the last 4 are used -- wasteful and potentially problematic for very long sessions.

### M3. [Resilience] Backend sends only last 4 history items but client sends all
**Severity:** MEDIUM
**Files:** `chainlit/app.py` (line 63), `backend/app/api/v1/routes/playground.py` (lines 191-192)

The Chainlit client sends the entire `conversation_history` on every request. The backend truncates to `[-4:]`. This mismatch means: (a) unnecessary network payload growth, (b) the client has a false model of what context the LLM actually sees. A user expecting the LLM to "remember" something from 10 messages ago will be confused.

### M4. [Security] No input validation on `document_ids` list
**Severity:** MEDIUM
**File:** `backend/app/schemas/playground.py` (lines 10, 17)

`document_ids: Optional[List[str]] = None` accepts any strings. The SQL uses `ANY(:doc_ids::uuid[])` which will cast to UUID -- PostgreSQL will reject invalid UUIDs, but this produces an unhandled 500 error instead of a clean 400 validation error. A very large list could also cause query performance issues.

### M5. [Docker] Chainlit container missing health check
**Severity:** MEDIUM
**File:** `docker/docker-compose.yml` (lines 87-100)

The chainlit service has no health check, unlike what would be expected for a production service. The `depends_on: - backend` only ensures start order, not readiness. If the backend is slow to start, Chainlit's `on_chat_start` will fail silently (the try/except at line 17-22 swallows the error).

### M6. [Docker] Chainlit container does not pass `PLAYGROUND_ENABLED` to backend
**Severity:** MEDIUM
**File:** `docker/docker-compose.yml` (lines 87-100)

The chainlit service only sets `BACKEND_URL: http://backend:8000`. It does not control whether the backend's playground is enabled. The backend's `PLAYGROUND_ENABLED` is set separately (line 39). This is fine if the user sets it, but the chainlit container will silently fail with confusing 403 errors if the backend isn't configured.

---

## Low Priority Issues

### L1. [Style] Embedding model name hardcoded in `steps.py`
**Severity:** LOW
**File:** `chainlit/ui/steps.py` (line 14)

`"model": "gemini-embedding-001"` is hardcoded. If the backend changes the embedding model, this display will be wrong. The backend response does not include the embedding model name.

### L2. [Style] `pyproject.toml` has placeholder readme URL
**Severity:** LOW
**File:** `chainlit/pyproject.toml` (line 5)

`readme = "https://github.com"` -- placeholder, not a real URL. Minor: not functional impact.

### L3. [Style] `top_k` not bounded from below
**Severity:** LOW
**File:** `backend/app/schemas/playground.py` (lines 9, 16)

`top_k` defaults to 10/5 but has no minimum constraint. A `top_k=0` would be capped to `min(0, 50) = 0` and return empty results silently.

---

## Edge Cases Found by Scout

1. **Network partition between Chainlit and backend:** If the backend goes down mid-session, the Chainlit app's `on_chat_start` swallows the error (line 20-22) and shows the "no documents" greeting. The user has no indication the backend is unreachable until they send a message. The `on_message` handler will then show a raw connection error.

2. **`document_ids` UUID validation gap:** Backend schema accepts `List[str]` for document_ids. Invalid UUIDs will cause a PostgreSQL cast error that surfaces as a 500, not a 400.

3. **Race in conversation history:** Between reading `conversation_history` from session (line 53) and setting it back (lines 56, 74), there is no locking. Under Chainlit's async model, if two messages are processed concurrently for the same session, history could be lost. This is likely safe given Chainlit's sequential message handling, but worth noting.

4. **`list_documents` silent failure hides backend issues:** On startup (line 17-22), if the backend returns a 500 or is unreachable, the app shows "RAG Playground ready" with zero documents. The user might think no documents exist when the backend is actually down.

5. **Similarity score inconsistency:** `rag_service.search()` rounds similarity to 4 decimal places (`round(float(row.similarity), 4)`). The playground routes use `float(row.similarity)` without rounding. This means the same query through `/api/v1/search` (authenticated) vs `/api/v1/playground/search` returns slightly different similarity values.

---

## Positive Observations

1. **SQL parameterization is correct** -- all user inputs go through SQLAlchemy `text()` with named parameters. No SQL injection risk.
2. **Env-var gating is consistent** -- all three endpoints check `PLAYGROUND_ENABLED` before processing. Default is `false`.
3. **Clean separation of concerns** -- `api/` handles HTTP, `ui/` handles rendering, `app.py` orchestrates. Good modularity.
4. **Docker profile gating** -- chainlit service uses `profiles: [playground]`, so it is opt-in and won't start by default.
5. **top_k capped at 50** -- prevents unbounded result sets.
6. **Pydantic models on both sides** -- type-safe contract between Chainlit and backend.

---

## Recommended Actions

1. **[CRITICAL]** Add defense-in-depth for playground: log a loud warning at startup when `PLAYGROUND_ENABLED=true`, consider adding IP allowlist or binding to localhost only. Document that this must never be exposed to the internet.
2. **[CRITICAL]** Sanitize error messages in `chainlit/app.py` -- catch `httpx.HTTPStatusError` and `httpx.ConnectError` separately, show generic user-facing messages, log the real error.
3. **[HIGH]** Create a shared `httpx.AsyncClient` instance in the Chainlit API client for connection pooling.
4. **[HIGH]** Add query length validation to `/search` endpoint (min 3 chars, max reasonable length like 2000).
5. **[HIGH]** Extract the shared SQL query into a helper function or reuse `rag_service.search()` with an option to pass pre-computed embeddings.
6. **[MEDIUM]** Truncate conversation history client-side to last 4 messages before sending.
7. **[MEDIUM]** Add Pydantic field validators for `document_ids` (valid UUID format) and `top_k` (min 1).

---

## Metrics

| Metric | Value |
|--------|-------|
| Type Coverage | ~100% (Pydantic on both sides) |
| Test Coverage | 0% -- no tests found for playground endpoints or Chainlit client |
| Linting Issues | Not run (no Bash access) |
| Files Reviewed | 9 |
| Total LOC | ~845 |

## Unresolved Questions

1. Is there a plan to add integration tests for the playground endpoints? Currently zero test coverage.
2. Should the playground endpoints be scoped to a specific user/organization for multi-tenant dev environments?
3. Is there a hard requirement that playground routes must never reach production, or is a network-level isolation planned?

---

**Status:** DONE_WITH_CONCERNS
**Summary:** Implementation is clean and well-structured. Critical concerns: playground endpoints expose all documents without tenant scoping (acceptable for local dev only if deployment safeguards exist), and Chainlit error handling leaks backend internals to the UI. High concerns: no connection pooling, missing query validation on search endpoint.
**Concerns:** Zero test coverage on new code. Error message information disclosure. No rate limiting on unauthenticated endpoints that trigger paid API calls.
