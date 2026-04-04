# Test Strategy: Full Pyramid for RAG Wiki App

**Date:** 2026-04-04
**Status:** Agreed (v2 — refined)
**Scope:** Backend (FastAPI) + Frontend (Vue 3) + E2E (Playwright) + Manual QA

---

## Problem Statement

No structured test process. Backend has 35 pytest tests with incomplete mocking. Frontend has zero tests. No E2E. No manual QA checklists. CI only runs backend tests, no frontend or coverage gating.

## Agreed Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Overall strategy | Full Test Pyramid | Beginner-friendly structure, clear separation |
| Backend framework | pytest + pytest-asyncio | Already in use, mature, well-documented |
| Frontend unit/component | Vitest + Vue Test Utils | Native Vite integration, fast, ESM support |
| E2E | Playwright | Multi-browser, better CI parallelization |
| Manual QA | Markdown checklists in `docs/testing/` | Simple, version-controlled, low overhead |
| Test DB | **Testcontainers PostgreSQL + pgvector** | Production parity — no SQLite divergence risk |
| Gemini mocking (unit) | `AsyncMock` at service boundary | Fast, deterministic, no API key needed |
| Gemini mocking (integration) | **VCR.py** — record real responses, replay cassettes | Mock data matches real API format |
| Redis mocking (unit) | `AsyncMock` | Fast, isolated |
| Redis mocking (integration) | **fakeredis** | In-memory Redis, catches serialization/TTL bugs |
| MinIO/S3 mocking (unit) | `AsyncMock` | Fast, isolated |
| MinIO/S3 mocking (integration) | **moto** | Mock S3 API, catches bucket/key/content-type issues |
| Celery mocking | `AsyncMock` (all tests) | Workers aren't system under test |
| CI gating | Lint + unit + integration + **E2E @smoke** on PR, full E2E nightly | Catches broken master early |
| Coverage targets | Backend 80%, Frontend stores 90%, Components 60% | Risk-based: higher for logic-heavy code |

---

## Test Pyramid

```
            ┌──────────────┐
            │   E2E Tests   │  ← Playwright (10-15 tests, slow, high confidence)
            │   (10-15)     │
       ┌────┴──────────────┴─────┐
       │  Integration Tests       │  ← API tests + real DB + fakeredis + moto + VCR (30-50)
       │  (30-50)                 │
  ┌────┴─────────────────────────┴────┐
  │  Unit Tests                        │  ← Services, stores, composables, AsyncMock (100+)
  │  (100+)                            │
  └────────────────────────────────────┘
```

---

## Database Testing: Testcontainers

### Why NOT SQLite

This project uses Postgres-specific features that SQLite cannot replicate:

| Postgres feature | Used in | SQLite gap |
|-----------------|---------|------------|
| `pgvector` extension | `database.py`, `document.py` | No vector type |
| `<=>` cosine distance | `rag_service.py` search/ranking | No equivalent |
| `::vector` cast | `rag_service.py` | No vector type |
| `::uuid` cast | `rag_service.py` | No UUID type |
| `ANY(:uuid[])` | `rag_service.py` | No array types |

**Every vector search query is untestable with SQLite.**

### Testcontainers Setup

```python
# conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from app.models.database import Base, get_db
from app.main import app

@pytest.fixture(scope="session")
def postgres_container():
    """Spin up real PostgreSQL + pgvector for entire test session."""
    with PostgresContainer("pgvector/pgvector:pg15") as pg:
        yield pg

@pytest.fixture(scope="session")
async def db_engine(postgres_container):
    """Create engine connected to real PostgreSQL."""
    url = postgres_container.get_connection_url().replace(
        "psycopg2", "asyncpg"
    )
    engine = create_async_engine(url, echo=False)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    """Create isolated DB session per test (rollback after each)."""
    async_session = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    """HTTP client with real PostgreSQL + dependency overrides."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
```

**Tradeoff:** ~2-5s container startup per session, then tests run fast. Acceptable for CI.

---

## Backend Testing

### Layer 1: Unit Tests (pytest)

**Target:** Services, models, schemas, utils — no DB, no external services

| Service | What to test | Mock strategy |
|---------|-------------|---------------|
| `llm_service` | Response formatting, error handling, empty key fallback | `AsyncMock` on `chat()` |
| `rag_service` | Text chunking logic, embedding normalization | `AsyncMock` on `embed()` / `embed_batch()` |
| `parsing` | PDF/docx/xlsx parsing, edge cases (empty, corrupt, large) | No mock (pure functions) |
| `permission_service` | Role checks, ownership validation, org membership | Mock DB session |
| `organization_service` | CRUD logic, member management, invitation flow | Mock DB session |

**Unit test fixtures:**
```python
# tests/unit/conftest.py
@pytest.fixture
def mock_llm_service():
    with patch("app.services.llm_service.llm_service") as mock:
        mock.chat = AsyncMock(return_value={
            "answer": "Test response",
            "sources": [],
            "model": "gemini-2.0-flash",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20}
        })
        yield mock

@pytest.fixture
def mock_rag_service():
    with patch("app.services.rag_service.rag_service") as mock:
        mock.embed = AsyncMock(return_value=[0.1] * 1536)
        mock.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
        yield mock

@pytest.fixture
def mock_minio():
    with patch("app.services.minio_service.minio_service") as mock:
        mock.upload_file = AsyncMock(return_value="test-bucket/test-key")
        mock.download_file = AsyncMock(return_value=b"test-content")
        yield mock

@pytest.fixture
def mock_celery():
    with patch("app.services.celery_tasks.process_document.delay") as mock:
        mock.return_value.id = "test-task-id"
        yield mock
```

### Layer 2: Integration Tests (pytest + httpx + Testcontainers)

**Target:** API endpoints against real PostgreSQL + real-ish external services

**Auth mock fix (applies to both unit & integration):**
```python
@pytest.fixture
async def auth_headers(client, db_session, test_user):
    """Override get_current_user dependency for authenticated tests."""
    from app.auth.security import get_current_user

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield {}  # No header needed — dependency overridden
    app.dependency_overrides.clear()
```

**Integration fixtures — fakeredis for Redis:**
```python
# tests/integration/conftest.py
import fakeredis.aioredis

@pytest.fixture
async def redis_client():
    """In-memory Redis that behaves like real Redis."""
    client = fakeredis.aioredis.FakeRedis()
    yield client
    await client.flushall()
```

**Integration fixtures — moto for MinIO/S3:**
```python
# tests/integration/conftest.py
from moto import mock_aws

@pytest.fixture
def mock_s3():
    """Mock S3 API for MinIO integration tests."""
    with mock_aws():
        import boto3
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        yield s3
```

**Integration fixtures — VCR.py for Gemini:**
```python
# tests/integration/conftest.py
import vcr

# Record once with real API key, replay forever after
gemini_vcr = vcr.VCR(
    cassette_library_dir="tests/fixtures/cassettes",
    record_mode="once",           # Record on first run, replay after
    match_on=["method", "uri"],   # Match requests by method + URL
)

@pytest.fixture
def gemini_cassette():
    """Use recorded Gemini API responses."""
    return gemini_vcr
```

```python
# tests/integration/test_chat.py
@gemini_cassette.use_cassette("gemini-chat-rag-response.yaml")
async def test_chat_with_document_context(client, auth_headers, db_session):
    """Test chat endpoint with VCR-recorded Gemini response."""
    response = await client.post("/api/v1/chat", json={
        "query": "What is the main topic?",
        "document_ids": ["..."]
    }, headers=auth_headers)
    assert response.status_code == 200
    assert "answer" in response.json()
```

**When to re-record VCR cassettes:**
- Gemini SDK update changes response format
- New prompt patterns added to `llm_service`
- Periodically (monthly) to catch silent API changes

### Test File Structure

```
backend/tests/
├── conftest.py                        # Shared: Testcontainers + DB engine + client
├── unit/
│   ├── conftest.py                    # Unit-only: AsyncMock fixtures
│   ├── test_llm_service.py
│   ├── test_rag_service.py
│   ├── test_parsing.py
│   ├── test_permission_service.py
│   ├── test_organization_service.py
│   └── test_schemas.py
├── integration/
│   ├── conftest.py                    # Integration: fakeredis + moto + VCR fixtures
│   ├── test_auth.py                   # (existing, fix mocking)
│   ├── test_documents.py              # (existing, fix mocking)
│   ├── test_search.py                 # Tests vector search against real pgvector
│   ├── test_chat.py                   # Tests RAG with VCR-recorded Gemini
│   ├── test_admin.py
│   ├── test_organizations.py
│   ├── test_invitations.py
│   └── test_groups.py
└── fixtures/
    ├── sample.pdf
    ├── sample.docx
    ├── sample.xlsx
    └── cassettes/                     # VCR recorded responses
        ├── gemini-chat-rag-response.yaml
        ├── gemini-embedding-query.yaml
        └── gemini-embedding-batch.yaml
```

---

## Frontend Testing

### Setup: Vitest + Vue Test Utils

**Install:**
```bash
pnpm add -D vitest @vitest/coverage-v8 jsdom @vue/test-utils
```

**vitest.config.ts:**
```ts
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    coverage: { provider: 'v8', reporter: ['text', 'html'] }
  }
})
```

### Layer 1: Unit Tests (Vitest)

**Priority order:**

| # | What | Why |
|---|------|-----|
| 1 | Auth store (`auth-store.ts`) | Core flow — login, logout, session, OAuth |
| 2 | Document store (`document-store.ts`) | CRUD + WebSocket state |
| 3 | Organization store (`organization-store.ts`) | CRUD + members |
| 4 | API client interceptors (`client.ts`) | Auth headers, token refresh, error handling |
| 5 | WebSocket composable (`use-web-socket.ts`) | Connection lifecycle, reconnection |

**Pinia store test pattern:**
```ts
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth-store'
import { mockSupabase } from '../helpers/mock-supabase'

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockSupabase.reset()
  })

  it('logs in with email/password', async () => { ... })
  it('handles OAuth callback', async () => { ... })
  it('clears state on logout', async () => { ... })
})
```

### Layer 2: Component Tests (Vitest + Vue Test Utils)

| Priority | Component | What to test |
|----------|-----------|-------------|
| High | LoginView | Form submission, validation, error display |
| High | RegisterView | Form submission, password match validation |
| High | DashboardView | Document list rendering, empty state |
| Medium | ChatView | Message sending, response display, source citations |
| Medium | SearchView | Search input, results rendering |
| Medium | DocumentDetailView | Document display, download |
| Low | AppLayout | Navigation, auth state display |

### Test File Structure

```
frontend/src/
├── __tests__/
│   ├── unit/
│   │   ├── stores/
│   │   │   ├── auth-store.test.ts
│   │   │   ├── document-store.test.ts
│   │   │   └── organization-store.test.ts
│   │   ├── composables/
│   │   │   └── use-web-socket.test.ts
│   │   └── api/
│   │       └── client.test.ts
│   └── components/
│       ├── LoginView.test.ts
│       ├── DashboardView.test.ts
│       └── ChatView.test.ts
├── __mocks__/
│   └── supabase.ts              # Global Supabase mock
└── ...
```

---

## E2E Testing (Playwright)

### Setup

```bash
pnpm add -D @playwright/test
npx playwright install
```

### Key Flows (10-15 tests)

| Flow | Tests | Priority | Smoke? |
|------|-------|----------|--------|
| Auth (login/register/logout) | 3-4 | P0 | **Yes — login + dashboard** |
| Document upload + processing | 2-3 | P0 | **Yes — upload + list** |
| Chat with document (RAG) | 2 | P0 | **Yes — send message + response** |
| Semantic search | 1-2 | P1 | **Yes — search + results** |
| Admin dashboard | 1-2 | P1 | **Yes — admin access** |
| Organization CRUD + members | 2-3 | P1 | No (full suite only) |

### Smoke Tests — Run on Every PR (3-5 tests)

Prevent "broken master for hours" — catch critical regressions immediately.

```typescript
// e2e/tests/auth.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Smoke @smoke', () => {
  test('login and see dashboard', async ({ page }) => {
    await page.goto('/login')
    await page.fill('[data-testid="email"]', 'test@example.com')
    await page.fill('[data-testid="password"]', 'password123')
    await page.click('[data-testid="login-btn"]')
    await expect(page).toHaveURL('/dashboard')
    await expect(page.locator('[data-testid="doc-list"]')).toBeVisible()
  })
})

test.describe('Smoke @smoke', () => {
  test('upload document and see in list', async ({ page }) => {
    // ... login first
    await page.setInputFiles('[data-testid="file-input"]', 'fixtures/test-doc.pdf')
    await page.click('[data-testid="upload-btn"]')
    await expect(page.locator('text=test-doc.pdf')).toBeVisible()
  })

  test('chat with document and get response', async ({ page }) => {
    // ... login + document exists
    await page.fill('[data-testid="chat-input"]', 'What is this document about?')
    await page.click('[data-testid="send-btn"]')
    await expect(page.locator('[data-testid="chat-response"]')).toBeVisible()
  })

  test('search returns results', async ({ page }) => {
    // ... login
    await page.fill('[data-testid="search-input"]', 'test query')
    await expect(page.locator('[data-testid="search-result"]')).toBeVisible()
  })

  test('admin can view user list', async ({ page }) => {
    // ... login as admin
    await page.goto('/admin')
    await expect(page.locator('[data-testid="user-table"]')).toBeVisible()
  })
})
```

### Run Strategy

| Trigger | What runs | Duration target |
|---------|-----------|----------------|
| **Every PR** | @smoke tests (3-5) | < 5 min |
| **Nightly** | Full E2E suite (10-15) | < 30 min |
| **Manual** | On-demand before releases | As needed |

```typescript
// playwright.config.ts
export default defineConfig({
  projects: [
    {
      name: 'smoke',
      testDir: './e2e/tests',
      testMatch: /.*\.spec\.ts/,
      grep: /@smoke/,  // Only smoke-tagged tests
    },
    {
      name: 'full',
      testDir: './e2e/tests',
      testMatch: /.*\.spec\.ts/,
      // All tests including non-smoke
    },
  ],
})
```

```yaml
# CI — PR: smoke only
- name: E2E Smoke Tests
  run: npx playwright test --project=smoke

# CI — Nightly: full suite
- name: Full E2E Suite
  run: npx playwright test --project=full
```

### Test File Structure

```
e2e/
├── playwright.config.ts
├── fixtures/
│   ├── test-document.pdf
│   └── auth.setup.ts              # Login state persistence
├── tests/
│   ├── auth.spec.ts               # @smoke: login + dashboard
│   ├── documents.spec.ts          # @smoke: upload + list
│   ├── chat.spec.ts               # @smoke: send + response
│   ├── search.spec.ts             # @smoke: search + results
│   ├── admin.spec.ts              # @smoke: admin access
│   └── organizations.spec.ts      # Full only
└── helpers/
    └── test-api.ts                # API helpers for test data seeding
```

---

## Manual QA Checklists

**Location:** `docs/testing/`

### Files to Create

| File | Content |
|------|---------|
| `docs/testing/smoke-test-checklist.md` | Quick pre-release sanity check (~15 min) |
| `docs/testing/auth-test-checklist.md` | Login, register, OAuth, session, token refresh |
| `docs/testing/document-test-checklist.md` | Upload, view, delete, access control, formats |
| `docs/testing/chat-search-test-checklist.md` | RAG chat quality, search relevance, edge cases |
| `docs/testing/admin-test-checklist.md` | User management, system stats, role enforcement |
| `docs/testing/organization-test-checklist.md` | Org CRUD, member invites, groups, permissions |

### Checklist Template

```markdown
# [Feature] Test Checklist

## Pre-conditions
- [ ] Local dev server running
- [ ] Test data seeded

## Happy Path
- [ ] Step 1: ...
- [ ] Step 2: ...

## Edge Cases
- [ ] Empty state
- [ ] Invalid input
- [ ] Network error

## Cross-cutting
- [ ] Mobile responsive
- [ ] Dark mode (if applicable)
- [ ] Accessibility (keyboard nav)
```

---

## CI/CD Integration

### GitHub Actions Pipeline

```
Every PR/Push:
  ├─ Lint (backend + frontend)
  ├─ Backend Unit Tests (pytest, no DB)
  ├─ Backend Integration Tests (pytest + Testcontainers + fakeredis + moto + VCR)
  ├─ Frontend Unit Tests (Vitest)
  ├─ Frontend Component Tests (Vitest)
  ├─ Frontend Build
  └─ E2E Smoke Tests (Playwright @smoke, 3-5 tests)
  → Block merge if ANY fail

Nightly (cron):
  └─ Full E2E Suite (Playwright, all tests, against Docker Compose)
  → Auto-create GitHub Issue on failure
```

### New CI Jobs Needed

1. **Frontend test job:** `pnpm test:coverage` (Vitest)
2. **Backend coverage:** `pytest --cov=app --cov-report=xml`
3. **E2E smoke on PR:** `npx playwright test --project=smoke`
4. **Nightly E2E full:** `npx playwright test --project=full` + failure issue
5. **Coverage badge:** Update README with coverage status

### PR Gating Rules

- All backend tests must pass
- All frontend tests must pass
- Frontend must build
- E2E smoke tests must pass
- No coverage regression > 5%

---

## New Dependencies

### Backend (pyproject.toml)

```
testcontainers[postgres]   # Real PostgreSQL in Docker for tests
asyncpg                     # Async PostgreSQL driver (for Testcontainers)
fakeredis                   # In-memory Redis for integration tests
moto                        # Mock AWS/S3 for MinIO integration tests
vcrpy                       # Record/replay Gemini API responses
pytest-cov                  # Coverage reporting
```

### Frontend (package.json)

```
vitest                      # Test runner
@vitest/coverage-v8         # Coverage provider
jsdom                       # DOM environment
@vue/test-utils             # Vue component testing
```

### E2E (package.json or root)

```
@playwright/test            # E2E test runner
```

---

## Coverage Targets

| Area | Target | Rationale |
|------|--------|-----------|
| Backend API routes | 80%+ | Critical business logic |
| Backend services | 70%+ | Complex RAG/permission logic |
| Frontend stores | 90%+ | State management is core |
| Frontend components | 60%+ | UI changes often, less ROI |
| E2E flows | Key flows only | 10-15 tests covering critical paths |

---

## Implementation Priority

| Phase | What | Effort |
|-------|------|--------|
| 1 | Fix backend auth mocking + Testcontainers setup + add service unit tests | High |
| 2 | Integration tests: fakeredis + moto + VCR fixtures | Medium |
| 3 | Setup Vitest + test auth store + API client | Medium |
| 4 | Frontend component tests (Login, Dashboard) | Medium |
| 5 | Setup Playwright + E2E smoke tests | High |
| 6 | Manual QA checklists | Low |
| 7 | CI/CD pipeline updates (smoke on PR, nightly full) | Medium |
| 8 | Remaining E2E + coverage targets | Ongoing |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Testcontainers startup time | Slow CI | Use `scope="session"` — one container for all tests (~2-5s) |
| VCR cassettes drift from real API | False confidence | Monthly re-record + integration tests catch format changes |
| Playwright flakiness in CI | False negatives | Retry logic, proper wait strategies, dedicated test data |
| Mock drift (AsyncMock doesn't match real behavior) | False confidence | VCR for Gemini, fakeredis for Redis, moto for S3 — near-real behavior |
| Coverage without quality | High % but poor tests | Focus on behavior assertions, not line coverage |
| Docker not available on developer machine | Can't run integration tests | Unit tests don't need Docker; integration tests run in CI |

---

## Unresolved Questions

1. Should E2E tests use a separate test Supabase project or mock auth entirely?
2. What's the threshold for blocking PRs on coverage regression?
3. Should we add visual regression testing (e.g., Playwright screenshots) in future?
4. Performance testing strategy — should we add load tests for the RAG pipeline?
5. VCR cassettes: store in git or generate in CI? (Recommend: store in git for reproducibility)
