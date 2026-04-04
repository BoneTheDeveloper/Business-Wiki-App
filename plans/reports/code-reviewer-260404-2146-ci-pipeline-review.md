# Code Review: CI Pipeline (`ci.yml`)

**Date:** 2026-04-04
**Reviewer:** code-reviewer
**Scope:** `.github/workflows/ci.yml`, `backend/tests/conftest.py`, `backend/pyproject.toml`
**Focus:** YAML correctness, CI best practices, coverage gate, security, testcontainers approach

---

## Overall Assessment

Well-structured CI pipeline. Two backend jobs (SQLite fast-path, pgvector integration path) plus frontend build. YAML syntax is valid. No critical security issues. A few production-readiness concerns below, mostly medium priority.

---

## Critical Issues

None.

---

## High Priority

### H1. Testcontainers container never stopped -- resource leak in CI

**File:** `backend/tests/conftest.py:51-58`

```python
pg = PostgresContainer("pgvector/pgvector:pg16")
pg.start()
url = pg.get_connection_url().replace("psycopg2", "asyncpg")
os.environ["_TC_PG_CONTAINER"] = pg.get_container_host_ip()
return url
```

The `PostgresContainer` is created and started but never stored for teardown. The `os.environ["_TC_PG_CONTAINER"]` line stores the host IP but not the container object itself. When the session ends, the container keeps running.

On GitHub Actions runners this is benign (runner VM is destroyed after the job), but:
- Local dev runs with `TEST_USE_DOCKER=true` will leak containers.
- The `_engine_url` fixture is a non-async `def` fixture returning a value, but `db_engine` is async. The testcontainers container starts synchronously in what is effectively an async test session. This works but is fragile -- if pytest-asyncio changes how it handles sync fixtures in async sessions, this breaks silently.

**Recommendation:** Store the container reference for cleanup. Use a session-scoped fixture that yields and then stops:

```python
@pytest.fixture(scope="session")
def _pg_container():
    pg = PostgresContainer("pgvector/pgvector:pg16")
    pg.start()
    yield pg
    pg.stop()
```

Then `_engine_url` consumes `_pg_container` instead of managing the lifecycle itself.

### H2. pgvector job collects 0 tests -- exits 0, masks real failures

**File:** `.github/workflows/ci.yml:68`

```yaml
run: uv run pytest tests/ -v --tb=short -m pgvector
```

When pytest selects `-m pgvector` and no tests carry that marker, pytest exits with code 0 and prints a warning. This means the pgvector job is a no-op that always passes, giving a false sense of coverage.

**Recommendation:** Add `--strict-markers` to the pytest invocation (already enforced at config level would be better), and consider adding a single trivial pgvector smoke test now so the job actually validates the container spin-up works. At minimum, add a comment in the CI file acknowledging this is intentionally a placeholder:

```yaml
# NOTE: No tests currently use @pytest.mark.pgvector.
# This job will be a no-op until pgvector tests are added.
run: uv run pytest tests/ -v --tb=short -m pgvector
```

Even better, add `--co` (collect-only) as a verification step to confirm the testcontainers setup works without needing actual test functions.

---

## Medium Priority

### M1. No caching for uv/pip dependencies

**File:** `.github/workflows/ci.yml:22-28`

Both backend jobs run `uv sync --frozen --dev` from scratch on every push. The `setup-uv` action handles uv tool caching, but the downloaded Python packages are re-resolved each time.

**Recommendation:** Add uv cache integration:

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v5
  with:
    enable-cache: true
    cache-dependency-glob: "backend/uv.lock"
```

This is available in `setup-uv@v4+` and will cache the uv store across runs.

### M2. Coverage artifact path inconsistency risk

**File:** `.github/workflows/ci.yml:39-43`

```yaml
- name: Upload coverage report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: coverage-report
    path: backend/coverage.xml
```

The artifact upload uses `if: always()`, which means it uploads even on test failure. This is intentional and good for debugging. However, note that `--cov-report=xml:coverage.xml` writes relative to the working directory (`backend/`), so the `path: backend/coverage.xml` is correct given the artifact is resolved from the repo root.

No action needed, but be aware: if you later add a second coverage-producing job (e.g., the pgvector job), the artifact name `coverage-report` will collide. Plan for namespacing now or later.

### M3. Coverage threshold of 50% is permissive

**File:** `.github/workflows/ci.yml:36`

`--cov-fail-under=50` means the pipeline passes with only half the codebase covered. This is reasonable for an initial rollout but should have a plan to ratchet up.

**Recommendation:** Add a TODO comment with a target and timeline:

```yaml
# TODO: Increase to 70% after initial test stabilization, target 80%
run: uv run pytest tests/ -v --tb=short --cov=app --cov-fail-under=50
```

### M4. `_engine_url` is a sync fixture that starts a Docker container

**File:** `backend/tests/conftest.py:48-59`

The `_engine_url` fixture is `def` (sync) but starts a Docker container via testcontainers. This is called during pytest's synchronous setup phase. If the Docker daemon is slow or the image needs pulling, this blocks the entire test session startup with no timeout.

**Recommendation:** Consider adding a timeout or at minimum documenting the expected first-run cost (pgvector image pull is ~150MB). For CI, this is fine since runners have good bandwidth, but local developers may be surprised.

### M5. `pytest_collection_modifyitems` runs even when `-m pgvector` is used

**File:** `backend/tests/conftest.py:34-43`

```python
def pytest_collection_modifyitems(config, items):
    if USE_DOCKER:
        return  # <-- When Docker is ON, pgvector tests are NOT skipped
```

When `TEST_USE_DOCKER=true`, the hook returns early and all tests run, including those without `@pytest.mark.pgvector`. This is correct behavior for the CI pgvector job (which uses `-m pgvector` to select), but if someone runs `pytest` locally with `TEST_USE_DOCKER=true` and without `-m pgvector`, they get ALL tests plus the Docker overhead.

This is intentional per the conftest docstring, but worth noting for future contributors.

---

## Low Priority

### L1. Frontend `pnpm/action-setup@v4` with `version: latest`

**File:** `.github/workflows/ci.yml:83-85`

```yaml
- name: Install pnpm
  uses: pnpm/action-setup@v4
  with:
    version: latest
```

Using `version: latest` is non-deterministic. A breaking change in pnpm could break CI unexpectedly.

**Recommendation:** Pin to a specific major version: `version: 9` or `version: 10`.

### L2. No explicit concurrency control

**File:** `.github/workflows/ci.yml` (top level)

No `concurrency` key. For a repo where multiple PRs may be open, this means every push triggers a full run. Not a problem at this scale, but worth considering:

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

### L3. No `timeout-minutes` on jobs or steps

Default timeout is 360 minutes per job. The testcontainers pgvector job could hang indefinitely if Docker has issues. Add:

```yaml
backend-test-pgvector:
  timeout-minutes: 10
```

---

## Security Review

| Check | Status |
|-------|--------|
| Secrets in workflow | PASS -- no secrets used or exposed |
| Untrusted checkout | PASS -- uses standard `actions/checkout@v4` |
| Privileged container | PASS -- no Docker-in-Docker, testcontainers runs on runner host |
| Artifact contents | PASS -- only coverage XML uploaded, no source/env data |
| PR trigger scope | PASS -- `pull_request` limited to `main` branch |
| Workflow permissions | NOTE -- no explicit `permissions` block; defaults to write token. Consider adding `permissions: contents: read` to least-privilege |

**Recommendation:** Add a top-level `permissions` block:

```yaml
permissions:
  contents: read
```

---

## Edge Cases

1. **First-run pgvector image pull**: If the pgvector Docker image is not cached on the runner, the pull adds 30-60s to the job. This is expected but undocumented.

2. **uv.lock missing**: `uv sync --frozen` will hard-fail if `uv.lock` is missing or out of date. The `uv.lock` file exists in `backend/`, so this is fine, but if someone edits `pyproject.toml` without re-running `uv lock`, CI will catch it. This is actually a feature, not a bug.

3. **Race in dependency overrides**: `conftest.py:104` sets `app.dependency_overrides[get_db]` and `conftest.py:151` sets `app.dependency_overrides[get_current_user]`. Since tests run sequentially by default with pytest-asyncio, this is safe. But if parallel test execution (`pytest-xdist`) is ever introduced, the shared `app` object's `dependency_overrides` dict will have race conditions.

---

## Positive Observations

1. Clean separation of SQLite (fast) and pgvector (integration) test paths.
2. `--cov-report=xml` + `actions/upload-artifact` enables future coverage badge/comment integrations.
3. `uv sync --frozen` enforces lockfile discipline.
4. Frontend build uses `pnpm install --frozen-lockfile` for reproducibility.
5. `pytest_configure` hook properly registers the `pgvector` marker, preventing "unknown marker" warnings.
6. Auth mocking via FastAPI dependency override is clean and avoids real Supabase calls in tests.

---

## Recommended Actions (Priority Order)

1. **Fix testcontainers container cleanup** (H1) -- leak affects local dev, not CI, but is a correctness issue.
2. **Add a smoke test or acknowledgment comment** for the pgvector job (H2) -- prevents false confidence from an always-green job.
3. **Add `permissions: contents: read`** to the workflow -- least-privilege default.
4. **Enable uv caching** via `setup-uv` cache options (M1) -- saves ~15-30s per run.
5. **Pin pnpm version** (L1) -- reproducibility.
6. **Add `timeout-minutes`** to pgvector job (L3) -- prevents Docker hangs from blocking CI indefinitely.

---

## Metrics

- YAML validity: PASS
- Test file count: 5 (auth, documents, search, chat, admin)
- Tests with `@pytest.mark.pgvector`: 0 (as expected per context)
- Coverage gate: 50% (permissive, acceptable for initial rollout)
- Linting issues: N/A (YAML review only)

---

## Unresolved Questions

1. Is there a plan to add the first `@pytest.mark.pgvector` test? The job is ready but currently a no-op.
2. Should the coverage threshold have a ratchet plan (e.g., 50% now, 70% in Q2, 80% in Q3)?
3. Is there intent to run coverage upload to an external service (Codecov, Coveralls) from the artifact?
