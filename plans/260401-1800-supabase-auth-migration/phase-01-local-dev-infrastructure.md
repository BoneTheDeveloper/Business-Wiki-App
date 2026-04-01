---
title: "Phase 1: Local Dev Infrastructure Setup"
phase: 1
status: pending
effort: 3h
depends_on: []
---

# Phase 1: Local Dev Infrastructure Setup

## Context
- Plan: [plan.md](plan.md)
- Files: `supabase/config.toml`, `docker/docker-compose.yml`, `supabase/migrations/*`

## Overview
Configure Supabase local stack as the primary auth + database provider. Remove standalone PostgreSQL from Docker Compose. Create migrations for user sync and custom JWT claims.

## Requirements

### Functional
- `supabase start` provides PostgreSQL (54322), GoTrue auth (54321), Studio (54323)
- Google OAuth works in local dev (or can be skipped with email)
- New row in `auth.users` automatically creates matching row in `public.users`
- JWT includes `app_role` claim from `public.users.role`

### Non-Functional
- Docker Compose only runs: Redis, MinIO, backend, frontend, Celery
- Backend DATABASE_URL points to Supabase PostgreSQL
- No duplicate database services

## Architecture

```
Developer Machine:
  supabase start
    -> PostgreSQL :54322 (with pgvector, auth schema)
    -> GoTrue     :54321 (auth API)
    -> Studio     :54323 (admin UI)
    -> Inbucket   :54324 (email testing)

  docker compose up
    -> Redis      :6379
    -> MinIO      :9000/9001
    -> Backend    :8000 -> connects to Supabase PG :54322
    -> Frontend   :5173 -> connects to Supabase Auth :54321
    -> Celery     -> connects to Supabase PG :54322 + Redis :6379
```

## Related Code Files

### Modify
- `supabase/config.toml` -- Enable Google OAuth provider, set site_url
- `docker/docker-compose.yml` -- Remove postgres service, update env vars
- `.env.example` -- Remove JWT/DB vars, keep Supabase vars
- `backend/.env.example` -- Remove JWT_SECRET_KEY/GOOGLE_* vars
- `frontend/.env.example` -- Already has VITE_SUPABASE_URL/KEY

### Create
- `supabase/migrations/20260401000001_sync_auth_users.sql` -- Trigger: auth.users -> public.users
- `supabase/migrations/20260401000002_custom_access_token_hook.sql` -- JWT custom claims

## Implementation Steps

### Step 1: Configure `supabase/config.toml` for Google OAuth

Add Google OAuth provider section. In local dev, Google OAuth requires `skip_nonce_check = true`.

```toml
# In supabase/config.toml, add after [auth.external.apple] section:

[auth.external.google]
enabled = true
client_id = "env(GOOGLE_CLIENT_ID)"
secret = "env(GOOGLE_CLIENT_SECRET)"
redirect_uri = "http://127.0.0.1:54321/auth/v1/callback"
skip_nonce_check = true
```

Also update `site_url` and `additional_redirect_urls`:
```toml
site_url = "http://127.0.0.1:5173"
additional_redirect_urls = ["http://127.0.0.1:5173/**"]
```

### Step 2: Create `public.users` sync trigger migration

File: `supabase/migrations/20260401000001_sync_auth_users.sql`

This trigger fires when a new user is inserted into `auth.users` (Supabase Auth signup). It creates a corresponding row in `public.users` with the user's email and default role.

```sql
-- Function to sync auth.users -> public.users
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, email, email_verified, name, avatar_url, role, is_active)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.email_confirmed_at IS NOT NULL, FALSE),
    COALESCE(NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1)),
    COALESCE(NEW.raw_user_meta_data->>'avatar_url'),
    'user',
    TRUE
  )
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    email_verified = EXCLUDED.email_verified,
    name = COALESCE(EXCLUDED.name, public.users.name),
    avatar_url = COALESCE(EXCLUDED.avatar_url, public.users.avatar_url),
    updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Fire trigger after new auth user is created
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Also sync on user update (email change, metadata change)
CREATE OR REPLACE FUNCTION public.handle_user_update()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE public.users SET
    email = NEW.email,
    email_verified = COALESCE(NEW.email_confirmed_at IS NOT NULL, FALSE),
    name = COALESCE(NEW.raw_user_meta_data->>'name', public.users.name),
    avatar_url = COALESCE(NEW.raw_user_meta_data->>'avatar_url', public.users.avatar_url),
    updated_at = now()
  WHERE id = NEW.id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_updated
  AFTER UPDATE ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_user_update();
```

### Step 3: Create custom access token hook migration

File: `supabase/migrations/20260401000002_custom_access_token_hook.sql`

This SQL function runs before JWT issuance and injects `app_role` claim from `public.users.role`.

```sql
-- Custom access token hook: inject app_role claim into JWT
CREATE OR REPLACE FUNCTION public.custom_access_token(event JSONB)
RETURNS JSONB AS $$
DECLARE
  claims JSONB;
  user_role VARCHAR(20);
BEGIN
  claims := event->'claims';

  -- Look up app role from public.users
  SELECT role INTO user_role
  FROM public.users
  WHERE id = (event->>'sub')::UUID;

  IF user_role IS NOT NULL THEN
    claims := jsonb_set(claims, '{app_role}', to_jsonb(user_role));
  END IF;

  RETURN claims;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execution to supabase_functions_admin (GoTrue uses this role)
GRANT EXECUTE ON FUNCTION public.custom_access_token(JSONB) TO supabase_functions_admin;
```

Then enable in `supabase/config.toml`:
```toml
[auth.hook.custom_access_token]
enabled = true
uri = "pg-functions://postgres/public/custom_access_token"
```

### Step 4: Update `docker/docker-compose.yml`

Remove the `postgres` service entirely. Update backend and celery to point to Supabase PostgreSQL (via host networking).

Key changes:
- Delete `postgres` service block
- Delete `postgres_data` volume
- Backend `DATABASE_URL`: `postgresql+asyncpg://postgres:postgres@host.docker.internal:54322/postgres`
- Celery `DATABASE_URL`: same
- Remove `depends_on: postgres` from backend and celery
- Remove `JWT_SECRET_KEY` from backend env
- Add `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` to backend/celery env

```yaml
services:
  redis:
    # ... unchanged ...

  minio:
    # ... unchanged ...

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@host.docker.internal:54322/postgres
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY:-minioadmin}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY:-minioadmin}
      SUPABASE_URL: ${SUPABASE_URL:-http://host.docker.internal:54321}
      SUPABASE_ANON_KEY: ${SUPABASE_ANON_KEY:-}
      SUPABASE_SERVICE_ROLE_KEY: ${SUPABASE_SERVICE_ROLE_KEY:-}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
    volumes:
      - ../backend:/app
      - backend_venv:/app/.venv
    depends_on:
      redis:
        condition: service_started
    extra_hosts:
      - "host.docker.internal:host-gateway"

  frontend:
    # ... unchanged except add env vars ...
    environment:
      VITE_SUPABASE_URL: ${SUPABASE_URL:-http://127.0.0.1:54321}
      VITE_SUPABASE_ANON_KEY: ${SUPABASE_ANON_KEY:-}

  celery_worker:
    # ... same DATABASE_URL as backend ...
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@host.docker.internal:54322/postgres
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY:-minioadmin}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY:-minioadmin}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### Step 5: Update `.env.example` files

**`.env.example`** (root) -- Remove JWT_SECRET_KEY, DB_USER/DB_PASSWORD/DB_NAME:
```env
# --- Supabase ---
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# --- Google OAuth (for Supabase Auth) ---
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# --- OpenAI ---
OPENAI_API_KEY=sk-your-openai-api-key

# --- MinIO ---
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

**`backend/.env.example`** -- Remove JWT_SECRET_KEY, GOOGLE_*, APP_URL, OAUTH_AUTO_REGISTER:
```env
# --- Supabase ---
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# --- Database (Supabase PostgreSQL) ---
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres

# --- Redis ---
REDIS_URL=redis://localhost:6379/0

# --- MinIO ---
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=documents
MINIO_SECURE=false

# --- OpenAI ---
OPENAI_API_KEY=sk-your-openai-api-key
```

**`frontend/.env.example`** -- Already correct, no changes needed.

### Step 6: Update `public.users` table schema

Create migration to remove password_hash, oauth_provider, oauth_id columns and add `auth_user_id` FK alignment.

File: `supabase/migrations/20260401000003_update_users_for_supabase.sql`

```sql
-- Remove columns now managed by Supabase Auth
ALTER TABLE public.users DROP COLUMN IF EXISTS password_hash;
ALTER TABLE public.users DROP COLUMN IF EXISTS oauth_provider;
ALTER TABLE public.users DROP COLUMN IF EXISTS oauth_id;

-- id column already UUID, will now reference auth.users.id directly
-- (no FK constraint needed since trigger maintains the relationship)

-- Drop OAuth-related index
DROP INDEX IF EXISTS public.ix_users_oauth_provider;
DROP INDEX IF EXISTS public.ix_users_oauth_provider_oauth_id;
```

## Todo Checklist

- [ ] Update `supabase/config.toml` with Google OAuth and custom hook config
- [ ] Create `20260401000001_sync_auth_users.sql` migration
- [ ] Create `20260401000002_custom_access_token_hook.sql` migration
- [ ] Create `20260401000003_update_users_for_supabase.sql` migration
- [ ] Update `docker/docker-compose.yml` -- remove postgres, update env vars
- [ ] Update `.env.example` -- remove JWT/DB vars
- [ ] Update `backend/.env.example` -- remove JWT/OAuth vars
- [ ] Run `supabase start` and verify all services running
- [ ] Run `supabase db reset` and verify migrations apply
- [ ] Test signup via Supabase Auth creates `public.users` row

## Success Criteria
- `supabase start` runs without errors
- `supabase db reset` applies all migrations
- Creating a user via Supabase Auth API (`POST /auth/v1/signup`) creates row in both `auth.users` and `public.users`
- JWT issued by Supabase contains `app_role` claim
- `docker compose up` starts Redis, MinIO, backend, frontend, Celery without PostgreSQL service
- Backend can connect to Supabase PostgreSQL from Docker container

## Risk Assessment
- **pgvector in Supabase local:** Supabase PG17 includes pgvector by default. Verify with `SELECT * FROM pg_available_extensions WHERE name = 'vector';`
- **host.docker.internal:** Works on Docker Desktop (Windows/Mac). Linux users need `extra_hosts` config (already included).
- **Google OAuth local:** Requires `skip_nonce_check = true`. Google OAuth redirect URI must match exactly.

## Security Considerations
- Google client secret uses env var substitution: `env(GOOGLE_CLIENT_SECRET)` -- never committed
- Sync trigger uses `SECURITY DEFINER` to ensure it runs as table owner
- Custom access token hook uses `SECURITY DEFINER` with explicit grant to `supabase_functions_admin`

## Next Steps
- Phase 2 depends on this phase completing (migrations must be in place)
- Backend migration can begin once migrations are verified
