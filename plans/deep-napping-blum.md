# Test Pyramid Implementation Plan

## Context

**Problem:** No structured test process. Backend has 30 tests on broken SQLite + placeholder auth. Frontend has zero tests. No E2E. No coverage gating. The existing tests silently pass despite broken auth mocking (`Bearer test-token-{user.id}` placeholder never validated by `get_current_user`).

**Goal:** Implement the agreed test strategy from `plans/reports/brainstorm-260404-2006-test-strategy-full-pyramid.md` — full test pyramid with Testcontainers, layered mocking, Vitest frontend, Playwright E2E, and CI updates.

**Outcome:** ~240 tests across 8 phases. Every phase independently deliverable and verifiable.

---

## Phase 1: Foundation — Testcontainers + Auth Mock Fix

**Goal:** Replace broken SQLite + placeholder-token setup with real PostgreSQL+pgvector and proper auth dependency overrides. All 30 existing tests must pass against real PG.

**Modify:**
- `backend/pyproject.toml` — add `testcontainers[postgres]>=4.0.0`, `pytest-cov>=6.0.0`; remove `aiosqlite`
- `backend/tests/conftest.py` — complete rewrite (see below)
- `backend/pytest.ini` — remove (move config to pyproject.toml `[tool.pytest.ini_options]`)

**conftest.py rewrite key changes:**
1. `postgres_container` fixture (session-scoped): `PostgresContainer("pgvector/pgvector:pg16")` → creates real PG with pgvector
2. `db_engine` fixture (session-scoped): async engine from container URL, runs `CREATE EXTENSION IF NOT EXISTS vector` + `Base.metadata.create_all`
3. `db_session` fixture (function-scoped): per-test session with rollback isolation
4. `auth_headers` fixture → override `get_current_user` dependency, NOT header injection:
   ```python
   app.dependency_overrides[get_current_user] = lambda: test_user
   ```
5. Remove deprecated `event_loop` fixture (pytest-asyncio 0.25+ handles this)
6. Remove `aiosqlite` import/usage entirely

**Verification:**
1. `uv sync --dev` succeeds
2. Docker running → `uv run pytest tests/ -v --tb=short` all 30 pass
3. No real HTTP calls to Supabase during test run

---

## Phase 2: Pure Service Unit Tests

**Goal:** Test services with zero external dependencies — pure logic functions. Cheapest tests, fastest feedback.

**Create:**
- `backend/tests/test_parsing.py` — `DocumentParser` static methods (~10 tests)
  - `get_format` valid/invalid/edge cases
  - `parse` for PDF/DOCX/XLSX using `tmp_path` + programmatic file generation
  - Unsupported format raises ValueError
- `backend/tests/test_permission_logic.py` — `PermissionService` static methods (~8 tests)
  - `ROLE_HIERARCHY` values: OWNER(4) > ADMIN(3) > MEMBER(2) > VIEWER(1)
  - `ROLE_PERMISSIONS` mapping: owner has all 6, viewer only VIEW
  - `_has_sufficient_access`: VIEW grant satisfies VIEW but not EDIT; EDIT satisfies both
- `backend/tests/test_rag_pure.py` — RAGService pure methods (~7 tests)
  - `chunk_text`: basic split, empty string, metadata preservation, single chunk
  - `_normalize`: zero vector, unit vector, result is L2-unit-length

**No new dependencies.** Uses pytest built-in `tmp_path`.

**Verification:** `uv run pytest tests/test_parsing.py tests/test_permission_logic.py tests/test_rag_pure.py -v`

**~25 new tests** (55 total)

---

## Phase 3: DB-Dependent Service Tests

**Goal:** Test CRUD services against real PostgreSQL+pgvector from Phase 1. No external APIs.

**Create:**
- `backend/tests/test_organization_service.py` (~15 tests) — create org, slug uniqueness, add/remove/update members, quota checks, usage stats
- `backend/tests/test_group_service.py` (~10 tests) — create/update/delete group, add/remove members, duplicate name validation
- `backend/tests/test_invitation_service.py` (~10 tests) — create/validate/accept/cancel/resend invitation, token hashing, rate limiting
- `backend/tests/test_permission_service.py` (~15 tests) — get_member_role, has_org_permission, can_manage_member, check_document_access (public/private/restricted), get_accessible_documents_query, can_upload_to_organization

**Modify conftest.py** — add fixtures:
- `test_organization` — creates org + owner member
- `test_user_in_org` — regular member in test org
- `test_group` — group in test org
- `test_document` — completed document owned by test_user

**Verification:** `uv run pytest tests/test_organization_service.py tests/test_group_service.py tests/test_invitation_service.py tests/test_permission_service.py -v`

**~50 new tests** (105 total)

---

## Phase 4: External Service Mocking + RAG/LLM Tests

**Goal:** Unit-test services calling external APIs using AsyncMock + fakeredis.

**Add dependency:** `fakeredis[lua]>=2.25.0` in pyproject.toml dev group

**Create:**
- `backend/tests/test_rag_service.py` (~12 tests)
  - AsyncMock on `genai.Client.aio.models.embed_content` for embed/embed_batch
  - DB integration test: insert chunks with real embeddings → `search()` with pgvector `<=>` operator
  - Edge: no API key raises ValueError, empty batch returns []
- `backend/tests/test_llm_service.py` (~8 tests)
  - AsyncMock on `genai.Client.aio.models.generate_content`
  - Context building, conversation history, API error fallback, safety filter fallback, no-key fallback
- `backend/tests/test_minio_service.py` (~8 tests)
  - Mock `Minio` client: upload/download/delete/exists/ensure_bucket
- `backend/tests/test_celery_tasks.py` (~7 tests)
  - Mock minio/rag/parsing services, test status transitions: pending→processing→completed/failed

**Key mock pattern (singleton patching):**
```python
@pytest.fixture
def mock_llm():
    with patch("app.services.llm_service.llm_service") as m:
        m.client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        yield m
```

**Verification:** `uv run pytest tests/test_rag_service.py tests/test_llm_service.py tests/test_minio_service.py tests/test_celery_tasks.py -v`

**~35 new tests** (140 total)

---

## Phase 5: Route Integration Tests + Coverage Baseline

**Goal:** HTTP-level tests for 4 untested routers. Establish coverage baseline.

**Create:**
- `backend/tests/test_organizations.py` (~10 tests) — CRUD, members, quota
- `backend/tests/test_invitations.py` (~8 tests) — send/accept/cancel/resend, rate limit
- `backend/tests/test_groups.py` (~8 tests) — CRUD, members
- `backend/tests/test_websocket.py` (~4 tests) — connect auth, status updates

**Modify `backend/pyproject.toml`:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=50"
```
Delete `backend/pytest.ini` (config moves to pyproject.toml).

**Verification:** `uv run pytest tests/ -v --cov=app --cov-report=term-missing` → 50%+ coverage

**~30 new tests** (170 total backend)

---

## Phase 6: Frontend Test Foundation (Vitest + Stores)

**Goal:** Set up Vitest, write tests for 3 Pinia stores.

**Modify:**
- `frontend/package.json` — add devDeps: `vitest`, `@vitest/coverage-v8`, `@vue/test-utils`, `@pinia/testing`, `msw`, `happy-dom`; add scripts: `test`, `test:watch`, `test:coverage`
- `frontend/vite.config.ts` — add `test` block (globals, happy-dom, setup files, coverage config)
- `frontend/tsconfig.json` — add vitest types

**Create:**
- `frontend/src/tests/setup.ts` — mock `@/lib/supabase` module
- `frontend/src/tests/stores/auth-store.test.ts` (~10 tests) — login/register/logout, session restore, PKCE handling, role detection
- `frontend/src/tests/stores/document-store.test.ts` (~10 tests) — fetch/upload/delete documents, status updates
- `frontend/src/tests/stores/organization-store.test.ts` (~10 tests) — CRUD, members, invitations, groups

**Verification:** `pnpm test` passes, `pnpm build` still works

**~30 new tests** (200 total)

---

## Phase 7: Frontend Components + Composables

**Goal:** Test Vue components and WebSocket composable.

**Create:**
- `frontend/src/tests/composables/use-web-socket.test.ts` (~8 tests) — connect/disconnect, reconnect, messages, send
- `frontend/src/tests/api/client.test.ts` (~4 tests) — auth header injection, 401 refresh retry
- Component tests for key views (~8 tests) — LoginView, DashboardView, ChatView rendering

**No new dependencies** (all from Phase 6).

**Verification:** `pnpm test` passes all frontend tests

**~20 new tests** (220 total)

---

## Phase 8: E2E + CI Pipeline

**Goal:** Playwright E2E with @smoke tags, CI updates for all test layers.

**Create:**
- `e2e/playwright.config.ts` — smoke + full projects, Docker Compose webServer
- `e2e/package.json` — `@playwright/test`
- `e2e/tests/auth.spec.ts` — @smoke: login, dashboard redirect
- `e2e/tests/documents.spec.ts` — @smoke: upload, list
- `e2e/tests/chat.spec.ts` — @smoke: send query, get response
- `e2e/tests/search.spec.ts` — @smoke: search returns results
- `e2e/tests/admin.spec.ts` — @smoke: admin access
- `e2e/tests/organizations.spec.ts` — full only: CRUD + members

**Modify:**
- `.github/workflows/ci.yml` — add frontend-test job, e2e-smoke job, coverage on backend
- Create `.github/workflows/e2e-nightly.yml` — cron `0 2 * * *`, full E2E suite

**Create docs:**
- `docs/testing/smoke-checklist.md` — 10-15 manual checks
- `docs/testing/full-qa-checklist.md` — comprehensive release checklist

**Verification:**
1. `npx playwright test --project=smoke` passes locally
2. CI pipeline runs all layers on test PR
3. Nightly workflow configured

**~15 E2E tests** (240+ total)

---

## Summary

| Phase | Scope | New Tests | Cumulative | Key Dep |
|-------|-------|-----------|------------|---------|
| 1 | Backend foundation | 0 (fix 30) | 30 | testcontainers, pytest-cov |
| 2 | Pure service units | 25 | 55 | — |
| 3 | DB service tests | 50 | 105 | — |
| 4 | External service mocks | 35 | 140 | fakeredis |
| 5 | Route integration + coverage | 30 | 170 | — |
| 6 | Frontend stores | 30 | 200 | vitest, vue-test-utils, msw |
| 7 | Frontend components | 20 | 220 | — |
| 8 | E2E + CI | 15 | 240+ | playwright |

**Critical files:** `backend/tests/conftest.py` (rewrite), `backend/app/dependencies.py` (auth override target), `backend/pyproject.toml` (deps), `frontend/vite.config.ts` (test config), `.github/workflows/ci.yml` (pipeline)

**Unresolved:**
1. PG image version: `pg16` or `pg17`? Verify against production Supabase version
2. E2E test data seeding strategy — seed script vs API-based creation
3. Frontend mocking: MSW vs direct `vi.mock` for API client — recommend `vi.mock` (simpler, KISS)
