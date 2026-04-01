---
title: "Phase 4: Testing & Cleanup"
phase: 4
status: pending
effort: 2h
depends_on: [phase-02, phase-03]
---

# Phase 4: Testing & Cleanup

## Context
- Plan: [plan.md](plan.md)
- Phase 2: [phase-02-backend-auth-migration.md](phase-02-backend-auth-migration.md)
- Phase 3: [phase-03-frontend-auth-migration.md](phase-03-frontend-auth-migration.md)

## Overview
End-to-end validation of the full auth flow, removal of unused dependencies, and documentation updates.

## Requirements

### Functional
- All auth flows work: signup, login, logout, Google OAuth, session refresh, page refresh persistence
- Role-based access control works: user, editor, admin endpoints enforce correct permissions
- Backend validates Supabase JWTs correctly (valid, expired, malformed tokens)
- New user signup auto-creates `public.users` row

### Non-Functional
- No leftover references to custom JWT, passlib, authlib, bcrypt in backend
- No leftover references to manual token storage in frontend
- Documentation reflects new auth architecture

## Related Code Files

### Verify
- `backend/pyproject.toml` -- deps cleaned up
- `backend/app/auth/` -- only `security.py`, `supabase.py`, `routes.py` remain
- `backend/app/services/` -- `oauth_service.py` deleted
- `frontend/package.json` -- `@supabase/supabase-js` added
- `docs/system-architecture.md` -- auth section updated
- `docs/codebase-summary.md` -- auth section updated

### Modify (docs)
- `docs/system-architecture.md`
- `docs/codebase-summary.md`

## Implementation Steps

### Step 1: Backend cleanup -- remove unused Python deps

Edit `backend/pyproject.toml` to remove:
- `passlib[bcrypt]` or `bcrypt` (if no other usage)
- `authlib` (OAuth handled by Supabase)
- `itsdangerous` (dependency of authlib, no direct usage)

Keep:
- `python-jose[cryptography]` -- still needed for JWT decode + RS256
- `httpx` -- needed for JWKS fetching

Run dependency sync:
```bash
cd backend
uv sync
```

### Step 2: Verify no dangling imports

Search for references to deleted modules:
```bash
# Backend
grep -r "from app.auth.oauth" backend/
grep -r "from app.services.oauth_service" backend/
grep -r "hash_password\|verify_password\|create_access_token\|create_refresh_token" backend/
grep -r "JWT_SECRET_KEY\|JWT_ALGORITHM\|JWT_EXPIRE_MINUTES" backend/
grep -r "GOOGLE_CLIENT_ID\|GOOGLE_CLIENT_SECRET\|GOOGLE_REDIRECT_URI" backend/
grep -r "passlib\|authlib\|itsdangerous" backend/
grep -r "password_hash\|oauth_provider\|oauth_id" backend/app/models/

# Frontend
grep -r "localStorage.setItem.*access_token\|localStorage.setItem.*refresh_token" frontend/src/
grep -r "localStorage.getItem.*access_token\|localStorage.getItem.*refresh_token" frontend/src/
grep -r "handleOAuthCallback\|oauth-callback" frontend/src/
```

All should return zero results.

### Step 3: Manual end-to-end test checklist

Run through each flow:

#### 3a. Fresh signup
1. Open app at `/login`
2. Navigate to `/register`
3. Enter email + password
4. Submit
5. Verify: user created in Supabase Auth (`supabase studio` -> Auth -> Users)
6. Verify: `public.users` row created with `role='user'`, `is_active=true`
7. Verify: JWT contains `app_role: "user"` claim

#### 3b. Email/password login
1. Logout if logged in
2. Enter registered email + password
3. Submit
4. Verify: redirected to dashboard
5. Verify: `GET /auth/me` returns user data
6. Verify: subsequent API calls include `Authorization` header

#### 3c. Session persistence
1. With active session, refresh page (F5)
2. Verify: still logged in, user data loads
3. Close tab, reopen app
4. Verify: session restored (Supabase persists in localStorage)

#### 3d. Google OAuth
1. Logout
2. Click "Google" button
3. Verify: redirects to Google login
4. Complete Google login
5. Verify: redirected back to app, logged in
6. Verify: `public.users` row created with name/avatar from Google profile

#### 3e. Logout
1. With active session, click logout
2. Verify: redirected to login page
3. Verify: `GET /auth/me` returns 401
4. Verify: cannot access protected routes

#### 3f. Token expiry / refresh
1. Login, wait for token to approach expiry (or shorten `jwt_expiry` in config.toml to 60s for testing)
2. Make an API call after token expiry
3. Verify: Supabase auto-refreshes token, API call succeeds
4. Verify: no 401 errors visible to user

#### 3g. Role-based access control
1. Create admin user (manually set `role='admin'` in `public.users`)
2. Verify: can access `/admin` routes
3. Login as regular user
4. Verify: cannot access `/admin` routes, redirected to dashboard

#### 3h. Invalid token handling
1. Login, get access token
2. Tamper with token (change one character)
3. Make API call
4. Verify: 401 response
5. Verify: frontend redirects to login (session recovery fails)

### Step 4: Backend compile check

```bash
cd backend
uv run python -c "from app.main import app; print('OK')"
uv run python -c "from app.auth.supabase import verify_supabase_token; print('OK')"
uv run python -c "from app.dependencies import get_current_user, require_admin; print('OK')"
```

### Step 5: Frontend build check

```bash
cd frontend
npm run build
```

Verify zero errors and zero warnings related to auth.

### Step 6: Update `docs/system-architecture.md`

Update the authentication section to reflect:
- Supabase Auth as the identity provider
- Backend JWT validation via JWKS (RS256)
- Custom access token hook for app_role claim
- User sync trigger (auth.users -> public.users)
- No password storage in backend

Key changes:
- Remove references to "custom JWT with HS256"
- Remove references to "bcrypt password hashing"
- Add Supabase Auth architecture diagram
- Update sequence diagrams for login/OAuth flows

### Step 7: Update `docs/codebase-summary.md`

Update to reflect:
- `backend/app/auth/supabase.py` -- new file
- `backend/app/auth/oauth.py` -- deleted
- `backend/app/services/oauth_service.py` -- deleted
- `frontend/src/lib/supabase.ts` -- new file
- Updated `backend/app/config.py` (removed JWT/OAuth vars)
- Updated `frontend/src/stores/auth-store.ts` (Supabase SDK)

### Step 8: Update `.env.example` files (final pass)

Verify all `.env.example` files are consistent:
- Root `.env.example` -- no JWT vars, has Supabase vars
- `backend/.env.example` -- no JWT/OAuth vars, has Supabase vars
- `frontend/.env.example` -- has `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`

## Todo Checklist

- [ ] Remove unused deps from `backend/pyproject.toml` (passlib, authlib, itsdangerous)
- [ ] Run `uv sync` to update lockfile
- [ ] Grep for dangling references to deleted modules/functions
- [ ] Fix any dangling references found
- [ ] Run backend compile check (`python -c "from app.main import app"`)
- [ ] Run frontend build check (`npm run build`)
- [ ] Manual test: signup flow
- [ ] Manual test: login flow
- [ ] Manual test: logout flow
- [ ] Manual test: Google OAuth flow
- [ ] Manual test: session persistence (page refresh)
- [ ] Manual test: token refresh
- [ ] Manual test: role-based access control
- [ ] Manual test: invalid token handling
- [ ] Update `docs/system-architecture.md`
- [ ] Update `docs/codebase-summary.md`
- [ ] Final `.env.example` consistency check

## Success Criteria
- Zero dangling imports/references to deleted auth code
- Backend starts and serves `/auth/me` with valid Supabase JWT
- Frontend builds without errors
- All 8 manual test flows pass
- Documentation updated to reflect new architecture
- No secrets or credentials in committed files

## Risk Assessment
- **Existing user data:** Users in the old `users` table with `password_hash` cannot log in after migration. This is expected for this phase (MVP). Future: write a one-time migration script to create Supabase Auth users from existing records.
- **Celery compatibility:** Celery workers use DATABASE_URL directly, no auth involved. Should work unchanged. Verify by triggering a document processing task.

## Security Considerations
- Verify no JWT secrets committed to git (check `.gitignore` covers `.env`)
- Verify Supabase service role key not exposed in frontend
- Verify RLS policies on `public.users` prevent unauthorized reads (if RLS enabled)
- Run `git diff --staged` before committing to catch accidental secret inclusion

## Unresolved Questions

1. **Existing user migration:** Should we write a script to migrate existing `users` table records to Supabase Auth? Not in scope for this plan but should be tracked as follow-up.
2. **social_accounts table:** Keep or drop? Currently kept to avoid breaking FKs. Consider dropping in a future cleanup migration.
3. **Supabase RLS policies:** The current migration `20260329000007_enable_rls.sql` enables RLS. Need to verify that RLS policies on `public.users` allow the sync trigger (which runs as `SECURITY DEFINER`) to INSERT/UPDATE. May need to add policy or exempt the trigger role.
4. **Custom access token hook in local dev:** The `pg-functions://` URI scheme for auth hooks may require specific Supabase CLI version. Verify compatibility with installed `supabase` CLI version.
5. **Docker Compose `host.docker.internal`:** This works on Windows/Mac Docker Desktop. If deploying to Linux production, the backend should use the Supabase project URL (cloud) instead of host networking. Document this in deployment guide.
