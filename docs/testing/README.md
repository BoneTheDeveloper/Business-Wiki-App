# Testing Hub — RAG Business Document Wiki

**Last Updated:** 2026-04-04

## File Tree

```
docs/testing/
├── README.md                    ← You are here (test strategy + navigation)
├── test-strategy-full-pyramid.md   ← Full test pyramid strategy (brainstorm output)
├── smoke-checklist.md           ← Manual smoke test checklist (Phase 8)
└── full-qa-checklist.md         ← Comprehensive release QA checklist (Phase 8)
```

## Test Architecture Overview

```
        ┌──────────┐
        │  E2E     │  Playwright — auth, docs, chat, search, admin
        │ ~15 tests│  CI: nightly full + PR smoke
        ├──────────┤
        │ Integration │  HTTP-level route tests (FastAPI TestClient)
        │ ~30 tests│  CI: every PR
        ├──────────┤
        │ Service  │  DB-dependent + external mock tests
        │ ~85 tests│  CI: every PR
        ├──────────┤
        │ Unit     │  Pure logic (parsing, permissions, RAG utils)
        │ ~25 tests│  CI: every PR
        └──────────┘
         Frontend: ~50 tests (Vitest + Vue Test Utils + MSW)
```

## Current Status

| Layer | Status | Tests | Notes |
|-------|--------|-------|-------|
| Backend Unit | Not started | 0 | Phase 2 pending |
| Backend Service (DB) | Not started | 0 | Phase 3 pending |
| Backend Service (Mock) | Not started | 0 | Phase 4 pending |
| Backend Integration | Partial | 29 | Existing route tests; CI has coverage gate (50%) |
| Frontend Stores | Not started | 0 | Phase 6 pending |
| Frontend Components | Not started | 0 | Phase 7 pending |
| E2E | Not started | 0 | Phase 8 pending |

## Test Commands

```bash
# Backend — all tests (SQLite mode, no Docker needed)
cd backend && uv run pytest tests/ -v

# Backend — with real PG + pgvector (Docker required)
TEST_USE_DOCKER=true uv run pytest tests/ -v

# Backend — with coverage report
uv run pytest tests/ -v --cov=app --cov-report=term-missing

# Frontend — when Vitest is set up (Phase 6+)
cd frontend && pnpm test
cd frontend && pnpm test:coverage

# E2E — when Playwright is set up (Phase 8+)
cd e2e && npx playwright test --project=smoke
cd e2e && npx playwright test
```

## CI Test Pipeline

```
PR to main/develop:
  ├── backend-test           → pytest (SQLite mode, coverage gate 50%)
  ├── backend-test-pgvector  → pytest -m pgvector (Testcontainers PG, placeholder)
  └── frontend-build         → pnpm build

Nightly:
  └── e2e-full               → playwright (all tests — Phase 8+)
```

## Key Conventions

- **Auth mocking:** FastAPI `dependency_overrides[get_current_user]` — never real Supabase calls
- **DB isolation:** Per-test `drop_all` + `create_all` for clean state
- **pgvector tests:** Marked `@pytest.mark.pgvector`, skipped unless `TEST_USE_DOCKER=true`
- **No mock data in tests:** Test against real services where possible (per project anti-patterns)
- **Frontend mocking:** Direct `vi.mock` for API client (KISS over MSW for store tests)

## Related Docs

| Topic | Location |
|-------|----------|
| Test strategy (full pyramid) | `docs/testing/test-strategy-full-pyramid.md` |
| Implementation plan | `plans/deep-napping-blum.md` |
| CI pipeline | `.github/workflows/ci.yml` |
| Code standards | `docs/conventions/code-standards.md` |
