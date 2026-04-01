# Code Review: Model Refactoring & Auth Migration

**Reviewer:** code-reviewer agent
**Date:** 2026-04-01
**BASE:** b242cf8 | **HEAD:** Working tree (unstaged)
**Scope:** 23 files changed -- backend models, schemas, auth, config, frontend OAuth/Docker

---

## Scope

- **Files:** 8 model files, 9 schema files, auth routes/security, config, 4 frontend views, Docker, pyproject.toml
- **LOC:** ~2800 changed/added
- **Focus:** Model split, schema extraction, bcrypt migration, OAuth flow, Docker config
- **Scout findings:** 3 new CRITICAL bugs beyond initial report

## Overall Assessment

Model refactoring into dedicated files is well-executed -- clean separation, proper re-export hub, backward-compatible `__init__.py`. Schema extraction follows same pattern. Auth migration to direct bcrypt is sound. However, the change from `SQLEnum` to `String(20)` for role/status columns introduced **3 runtime-crash bugs** in code that assumes enum objects are returned from DB queries. Docker compose has a driver mismatch that will prevent container startup. JWT tokens are passed in URL query params (security concern).

---

## CRITICAL Issues

### C1. `admin.py:134` -- `.value` on plain string crashes at runtime
**File:** `backend/app/api/v1/routes/admin.py:134`
**Code:** `by_status = {row[0].value: row[1] for row in status_result}`
**Problem:** `Document.status` is now `Column(String(20))`. When SQLAlchemy reads this VARCHAR column, it returns a plain `str` (e.g., `"completed"`). The code calls `.value` on it, which will raise `AttributeError: 'str' object has no attribute 'value'`. This crashes the `/admin/stats` endpoint every time.
**Fix:** Change to `row[0]` (it is already a string):
```python
by_status = {row[0]: row[1] for row in status_result}
```

### C2. `celery_tasks.py` -- `doc.metadata` does not exist, should be `doc.doc_metadata`
**File:** `backend/app/services/celery_tasks.py:71,72,82,179,199`
**Code:** `doc.metadata = {...}`, `**doc.metadata`, `rag_service.chunk_text(parsed['text'], doc.metadata)`
**Problem:** The `Document` model has `doc_metadata` (aliased in schema), not `metadata`. Similarly, `DocumentChunk` has `chunk_metadata`, not `metadata`. Lines 71, 72, 82, 97, 179, 194, 199 all reference the wrong attribute name. This will crash document processing every time with `AttributeError: 'Document' object has no attribute 'metadata'`.
**Fix:** Replace all `doc.metadata` with `doc.doc_metadata` and `metadata=chunk.get(...)` with `chunk_metadata=chunk.get(...)`.

### C3. `celery_tasks.py:51,105,122` -- Assigning enum to String column
**File:** `backend/app/services/celery_tasks.py:51,105,122`
**Code:** `doc.status = DocumentStatus.PROCESSING` / `DocumentStatus.COMPLETED` / `DocumentStatus.FAILED`
**Problem:** Column is `String(20)`. Assigning a `DocumentStatus` enum works because `str(DocumentStatus.PROCESSING)` == `"DocumentStatus.PROCESSING"` (the class name, NOT `"processing"`). SQLAlchemy converts via `str()`, not `.value`. This stores the WRONG string in the DB.
**Verification:** `str(DocumentStatus.PROCESSING)` returns `"DocumentStatus.PROCESSING"`, not `"processing"`. The model default uses `DocumentStatus.PENDING.value` correctly, but the celery task does NOT use `.value`.
**Fix:** Use `doc.status = DocumentStatus.PROCESSING.value` (add `.value`).

---

## IMPORTANT Issues

### I1. Docker Compose DATABASE_URL uses sync driver, backend expects async
**File:** `docker/docker-compose.yml:44,80`
**Code:** `DATABASE_URL: postgresql://${DB_USER:-wiki}:...`
**Problem:** Backend uses `asyncpg` driver (`postgresql+asyncpg://`). Docker compose passes `postgresql://` (sync driver). The backend will fail to connect with `cannot use sync driver with async engine`.
**Fix:** Change to `postgresql+asyncpg://` in docker-compose.yml:
```yaml
DATABASE_URL: postgresql+asyncpg://${DB_USER:-wiki}:${DB_PASSWORD:-wiki_secret}@postgres:5432/${DB_NAME:-wiki_db}
```

### I2. `passlib[bcrypt]` is dead dependency in pyproject.toml
**File:** `backend/pyproject.toml:16`
**Code:** `"passlib[bcrypt]>=1.7.4",`
**Problem:** `security.py` migrated to direct `bcrypt` library. `passlib[bcrypt]` is still declared, pulling in `passlib` + `bcrypt` as transitive deps unnecessarily. Also need to add `bcrypt>=4.0.0` as an explicit dependency since it is now used directly.
**Fix:** Replace `passlib[bcrypt]>=1.7.4` with `bcrypt>=4.0.0`.

### I3. OAuth tokens passed in URL query string (security)
**File:** `backend/app/auth/routes.py:174`
**Code:** `frontend_url = f"{settings.APP_URL}/oauth/callback?access_token={access_token}&refresh_token={refresh_token}..."`
**Problem:** JWT tokens are passed in URL query params. These get logged in browser history, proxy logs, referrer headers, and server access logs. This is an OWASP sensitive-data-exposure risk.
**Fix:** Use a short-lived one-time code exchange pattern: return a `code` in the URL, then the frontend makes a POST to exchange it for tokens. Or use the fragment (`#`) approach which does not get sent to servers.

### I4. PKCE removed from OAuth without documented justification
**File:** `backend/app/auth/routes.py`
**Problem:** PKCE (Proof Key for Code Exchange) was removed from the Google OAuth flow. This reduces security -- if an authorization code is intercepted (e.g., via compromised redirect URI), it can be exchanged without the `code_verifier`. Server-side OAuth is lower risk than SPA, but PKCE is still recommended by OAuth 2.1 spec.
**Recommendation:** Document why PKCE was removed, or re-add it.

### I5. `datetime.utcnow()` is deprecated (Python 3.12+)
**Files:** All model files, `security.py`, `celery_tasks.py`, all service files
**Count:** 30+ occurrences across the codebase
**Problem:** `datetime.utcnow()` returns a naive datetime without timezone info. Deprecated in Python 3.12. Will emit `DeprecationWarning` now and may be removed in future Python.
**Fix:** Use `datetime.now(timezone.utc)` or `func.now()` for server-side DB defaults. For SQLAlchemy `default=`, prefer `func.now()` over Python-side evaluation.

### I6. Duplicate schema definitions in admin.py route
**File:** `backend/app/api/v1/routes/admin.py:18-39`
**Code:** Inline `UserUpdate`, `UserListResponse`, `StatsResponse` classes
**Problem:** Same-named schemas already exist in `app/schemas/admin.py` and `app/schemas/user.py`. The inline `StatsResponse` differs from the schemas version (has extra `active_users` field). This violates DRY and creates confusion about which schema is the source of truth.
**Fix:** Import from `app.schemas` and add `active_users` to the canonical schema.

---

## MEDIUM Issues

### M1. Comment in models.py references wrong file names
**File:** `backend/app/models/models.py:7,10`
**Code:** `- social-account.py: SocialAccount` and `- document-access.py: DocumentAccess`
**Problem:** Comments use hyphens (`social-account.py`) but actual files use underscores (`social_account.py`, `document_access.py`).
**Fix:** Update comments to match actual filenames.

### M2. `require_role` comparison relies on `str, Enum` behavior
**File:** `backend/app/dependencies.py:49`
**Code:** `if user.role not in roles:`
**Problem:** `user.role` is a plain string (VARCHAR column), `roles` is `List[UserRole]`. Works because `UserRole(str, Enum)` makes `"admin" == UserRole.ADMIN` return `True`. But this is fragile -- if anyone changes the enum base class or the column type, it silently breaks.
**Recommendation:** Add a comment explaining the str-enum comparison contract, or normalize explicitly.

### M3. `handleGoogleLogin` try/catch is useless
**File:** `frontend/src/views/LoginView.vue:53-59`
**Code:** `try { window.location.href = ... } catch (error) { ... }`
**Problem:** `window.location.href` assignment triggers navigation, so the catch block is unreachable. Any errors would be from string interpolation, not from navigation.
**Fix:** Remove the try/catch or add a comment explaining it is for build-time safety.

### M4. `__init__.py` imports from `app.models.database` which is not in the models directory
**File:** `backend/app/models/__init__.py:2`
**Code:** `from app.models.database import Base, engine, AsyncSessionLocal, get_db, init_db`
**Problem:** The models `__init__.py` imports database infrastructure alongside model definitions. This means importing any model triggers database connection setup. Separation of concerns issue.
**Recommendation:** Move DB infrastructure imports to a separate import path.

### M5. Schema `__init__.py` imports duplicate `InvitationCreate`/`InvitationResponse`/`InvitationAccept`/`InvitationList`
**File:** `backend/app/schemas/__init__.py:12-16` and `backend/app/schemas/organization.py:67-94`
**Problem:** These schemas are defined in both `schemas/invitation.py` AND `schemas/organization.py` (identical classes). The `__init__.py` imports them from `organization.py`. This is a DRY violation.
**Fix:** Define in `invitation.py` only, import in `organization.py` if needed for re-export.

---

## LOW Issues

### L1. Frontend Dockerfile pins pnpm@9.15.4
**File:** `frontend/Dockerfile.dev:7`
**Note:** Good practice for reproducibility. Verify compatibility with `pnpm-lock.yaml`.

### L2. `GOOGLE_REDIRECT_URI` defaults to `localhost:5173`
**File:** `backend/app/config.py:37`
**Note:** Fine for local dev, but `APP_URL` and `GOOGLE_REDIRECT_URI` should be validated as matching in production. Consider adding a startup check.

### L3. Vite proxy target uses `process.env` instead of `loadEnv`
**File:** `frontend/vite.config.ts:17`
**Code:** `target: process.env.VITE_API_URL || 'http://localhost:8000'`
**Problem:** In Vite, `process.env.VITE_*` variables are only available in app code (via `define`/`import.meta.env`). In `vite.config.ts`, they need `loadEnv()` from `vite`. This will always fall back to the default.
**Fix:** Use `loadEnv()`:
```ts
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return { ... config with env.VITE_API_URL ... }
})
```

---

## Positive Observations

1. **Model refactoring** is clean and well-structured. Each model in its own file, proper re-export in `models.py` and `__init__.py` for backward compatibility.
2. **Schema extraction** follows same pattern -- good consistency.
3. **bcrypt migration** is correct -- direct bcrypt is simpler and avoids the passlib/bcrypt 5.x compatibility issue.
4. **OAuth CSRF state** is properly implemented with `secrets.token_urlsafe(32)` and session validation.
5. **`OAuthCallbackView.vue`** handles error cases well -- missing tokens, errors, and redirects back to login with proper error messages.
6. **Frontend router** properly marks OAuth callback as `guest` route to avoid auth redirect loops.
7. **File size management** is good -- each model file is well under 200 lines.
8. **DocumentAccess CHECK constraint** for XOR between user_id and group_id is a good DB-level integrity check.

---

## Recommended Actions

| Priority | Action | Effort |
|----------|--------|--------|
| CRITICAL | Fix `row[0].value` in `admin.py:134` | 1 min |
| CRITICAL | Fix `doc.metadata` -> `doc.doc_metadata` in `celery_tasks.py` | 5 min |
| CRITICAL | Add `.value` to `DocumentStatus` assignments in `celery_tasks.py` | 2 min |
| IMPORTANT | Fix `DATABASE_URL` driver in `docker-compose.yml` | 2 min |
| IMPORTANT | Replace `passlib[bcrypt]` with `bcrypt` in `pyproject.toml` | 1 min |
| IMPORTANT | Move OAuth token exchange to code-flow or POST body | 30 min |
| IMPORTANT | Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` | 15 min |
| IMPORTANT | Deduplicate inline admin schemas, use `app.schemas` imports | 10 min |
| MEDIUM | Fix model file name comments in `models.py` | 1 min |
| MEDIUM | Fix `loadEnv` in `vite.config.ts` | 5 min |
| MEDIUM | Remove duplicate invitation schemas between `invitation.py` and `organization.py` | 5 min |

---

## Metrics

- **Type Coverage:** ~80% (schemas are typed, but inline schema definitions in admin.py bypass the system)
- **Test Coverage:** Unknown (no test files changed in this diff)
- **Linting Issues:** Not run (no linter output available)
- **Runtime Crash Bugs:** 3 confirmed (C1, C2, C3)

---

## Unresolved Questions

1. Why was PKCE removed from OAuth? Was there a specific incompatibility or just simplification?
2. Are there existing DB migrations that handle the `SQLEnum -> VARCHAR` column type change, or is this a fresh DB with no migration history?
3. The `supabase/` directory is untracked -- is local Supabase stack the intended dev environment, or is Docker Compose still needed?
4. `celery_tasks.py` uses `await` inside Celery (sync framework). Is this running with `gevent`/`eventlet` pool, or is there a custom async bridge? This could be a separate issue worth investigating.
