---
title: "Migrate Custom JWT Auth to Supabase Auth"
description: "Replace custom JWT/password/OAuth implementation with Supabase Auth for all user management, session handling, and OAuth flows."
status: pending
priority: P1
effort: 16h
branch: main
tags: [auth, supabase, migration, backend, frontend]
created: 2026-04-01
---

# Plan: Migrate Custom JWT Auth to Supabase Auth

## Summary
Replace custom JWT creation/verification, bcrypt password hashing, and authlib Google OAuth with Supabase Auth. Backend becomes a pure JWT validator (JWKS). Frontend uses `@supabase/supabase-js` for all auth operations.

## Architecture Shift

```
BEFORE:  Frontend --> Backend (creates JWT) --> PostgreSQL (users table with password_hash)
AFTER:   Frontend --> Supabase Auth (issues JWT) --> Backend (validates JWT via JWKS) --> PostgreSQL (public.users, no passwords)
```

- **Supabase owns:** signup, login, password reset, email verification, OAuth, sessions, JWT issuance
- **Backend owns:** JWT validation via JWKS, user lookup from `public.users`, role-based access control
- **Frontend owns:** Supabase client SDK, session management, auth state

## Phases

| # | Phase | Status | Est | File |
|---|-------|--------|-----|------|
| 1 | Local Dev Infrastructure | pending | 3h | [phase-01-local-dev-infrastructure.md](phase-01-local-dev-infrastructure.md) |
| 2 | Backend Auth Migration | pending | 6h | [phase-02-backend-auth-migration.md](phase-02-backend-auth-migration.md) |
| 3 | Frontend Auth Migration | pending | 5h | [phase-03-frontend-auth-migration.md](phase-03-frontend-auth-migration.md) |
| 4 | Testing & Cleanup | pending | 2h | [phase-04-testing-cleanup.md](phase-04-testing-cleanup.md) |

## Key Decisions

1. **User sync strategy:** Supabase trigger on `auth.users` insert calls SQL function to upsert `public.users` row. Backend never creates users; only reads them.
2. **Role storage:** App role stored in `public.users.role` column (existing). JWT carries `app_role` claim via Supabase Custom Access Token Hook reading from `public.users`. Backend can also read role from DB directly as fallback.
3. **social_accounts table:** Keep but stop writing to it. Supabase tracks identities in `auth.identities`. Future cleanup to remove.
4. **Celery workers:** No auth needed for workers; they use service role / direct DB access. No changes required.

## Dependencies Between Phases

```
Phase 1 (infrastructure) --> Phase 2 (backend) --> Phase 3 (frontend) --> Phase 4 (testing)
```

Phases 2 and 3 can partially overlap once Phase 1 is done (backend and frontend changes are independent).

## Files Created/Modified

### Created
- `frontend/src/lib/supabase.ts` -- Supabase client init
- `backend/app/auth/supabase.py` -- JWT verification via JWKS
- `supabase/migrations/YYYYMMDD_sync_auth_users.sql` -- Auth user sync trigger
- `supabase/migrations/YYYYMMDD_custom_access_token_hook.sql` -- Custom JWT claims

### Modified
- `backend/app/auth/security.py` -- Remove JWT creation, keep JWKS validation
- `backend/app/auth/routes.py` -- Remove login/register/oauth, keep /auth/me
- `backend/app/dependencies.py` -- Use Supabase JWT validation
- `backend/app/config.py` -- Remove JWT_SECRET_KEY, keep Supabase vars
- `backend/app/models/user.py` -- Remove password_hash, oauth_provider, oauth_id columns
- `backend/app/models/__init__.py` -- Update imports
- `frontend/src/stores/auth-store.ts` -- Use Supabase SDK
- `frontend/src/views/LoginView.vue` -- Use Supabase signIn methods
- `frontend/src/views/OAuthCallbackView.vue` -- Handle Supabase OAuth redirect
- `frontend/src/api/client.ts` -- Get token from Supabase session
- `frontend/src/router/index.ts` -- Use Supabase session for guards
- `docker/docker-compose.yml` -- Remove PostgreSQL service
- `supabase/config.toml` -- Enable Google OAuth
- `.env.example`, `backend/.env.example`, `frontend/.env.example`

### Deleted
- `backend/app/auth/oauth.py` -- Supabase handles OAuth
- `backend/app/services/oauth_service.py` -- No longer needed

## Risk Assessment
- **Existing user migration:** Not in scope for MVP. Start fresh with Supabase Auth. Document migration path for future.
- **JWKS caching:** Must cache keys with TTL to avoid hitting Supabase on every request.
- **Docker networking:** Backend in Docker needs to reach Supabase PostgreSQL (host.docker.internal or Supabase URL).
