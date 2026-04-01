# Supabase Local Development Setup Research Report

**Date:** 2026-04-01
**Research Focus:** Supabase local setup, Docker Compose coexistence, migrations, configuration

---

## 1. `supabase start` — Container Setup

### Containers Started
`supabase start` spins up these Docker containers:
- **PostgreSQL** (54322) — Database with pgvector extension
- **GoTrue** (54321) — Authentication service
- **PostgREST** (54321) — REST API gateway
- **Realtime** — WebSocket subscriptions
- **Studio** (54323) — Web dashboard UI
- **db-mailer** (54324) — Email testing server (HTTP UI)
- **pgbouncer** (54329) — Connection pooler
- **pg_graphql** — GraphQL API
- **Inbucket** — Email testing UI
- **Vector** — If enabled for embeddings

### Default Ports
- **54321** — API URL (GoTrue, PostgREST, GraphQL)
- **54322** — Database connection
- **54323** — Supabase Studio dashboard
- **54324** — Email testing server (Inbucket)
- **54329** — PgBouncer connection pooler

### Configuration File
Located at `supabase/config.toml` — controls all service settings:
- Project ID (`project_id`)
- API settings (port, schemas, TLS)
- Database settings (port, version, migrations)
- Auth settings (site_url, JWT expiry, password requirements)
- Realtime, Studio, Storage, Email settings

---

## 2. Coexistence with Docker Compose

### Current Setup (before migration)
Docker Compose runs: PostgreSQL, Redis, MinIO, backend, frontend, Celery

### After Supabase Migration (recommended)
Docker Compose should ONLY run:
- Redis
- MinIO
- backend
- frontend
- Celery

**PostgreSQL removed** — Supabase provides PostgreSQL via `supabase start`

### Connection String Configuration

**Local Development:**
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres
```

**Remote Supabase:**
```bash
DATABASE_URL=postgresql+asyncpg://postgres.[project-ref]:[password]@aws-0-region.pooler.supabase.com:5432/postgres
```

**Key points:**
- Use `postgresql+asyncpg` driver (Django/SQLAlchemy compatible)
- Local: host `127.0.0.1`, port `54322`, user `postgres`, password `postgres`
- Remote: Uses pooler connection (not direct), port `5432`

### Updated Docker Compose
Create `docker/docker-compose.yml` WITHOUT postgres service:

```yaml
services:
  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
      JWT_SECRET_KEY: ${JWT_SECRET_KEY:-change-me-in-production}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
    volumes:
      - ../backend:/app
      - backend_venv:/app/.venv
    depends_on:
      - redis
      - minio

  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:5173"
    environment:
      VITE_API_URL: http://backend:8000
    volumes:
      - ../frontend:/app
      - frontend_node_modules:/app/node_modules
    depends_on:
      - backend

  celery_worker:
    build:
      context: ../backend
      dockerfile: Dockerfile
    command: uv run celery -A app.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
    volumes:
      - ../backend:/app
      - backend_venv:/app/.venv
    depends_on:
      - redis
      - minio

volumes:
  redis_data:
  minio_data:
  frontend_node_modules:
  backend_venv:
```

**Note:** Remove the `depends_on` clause that references postgres (line 54-56 in original docker-compose.yml)

---

## 3. Supabase Migrations

### Migration Files Location
`supabase/migrations/` directory — SQL files named with timestamps:
```
supabase/migrations/
├── 20260329000001_enable_extensions.sql
├── 20260329000002_create_users.sql
├── 20260329000003_create_organizations.sql
├── 20260329000004_create_org_members_groups.sql
├── 20260329000005_create_documents.sql
├── 20260329000006_create_access_invitations_social.sql
└── 20260329000007_enable_rls.sql
```

### Migration Commands

**Apply migrations locally:**
```bash
supabase db push
```
Pushes changes from migration files to local PostgreSQL database.

**Check schema differences:**
```bash
supabase db diff
```
Shows what changes exist between migration files and actual database state.

**Create new migration:**
```bash
supabase migration new migration_name
```
Creates a new SQL file with current timestamp.

**Reset database (destructive):**
```bash
supabase db reset
```
Applies all migrations and seed data, drops all data.

**Important config in `supabase/config.toml`:**
```toml
[db.migrations]
enabled = true
schema_paths = []  # Optional: specify custom schema paths

[db.seed]
enabled = true
sql_paths = ["./seed.sql"]  # Run seed.sql after migrations
```

### Seed Data
- `supabase/seed.sql` — Seed data file
- Automatically runs after migrations during `supabase db reset`
- Can be disabled in config.toml if not needed

---

## 4. Supabase config.toml

### Key Sections

**Project settings:**
```toml
project_id = "Bussiness_Wiki_App"
```

**API (54321):**
```toml
[api]
enabled = true
port = 54321
schemas = ["public", "graphql_public"]
extra_search_path = ["public", "extensions"]
max_rows = 1000
```

**Database (54322):**
```toml
[db]
port = 54322
shadow_port = 54320
major_version = 17
pooler.enabled = false
pooler.port = 54329
```

**Studio (54323):**
```toml
[studio]
enabled = true
port = 54323
api_url = "http://127.0.0.1"
openai_api_key = "env(OPENAI_API_KEY)"
```

**Auth (Google OAuth):**
```toml
[auth]
enabled = true
site_url = "http://127.0.0.1:3000"
additional_redirect_urls = ["https://127.0.0.1:3000"]
enable_signup = true
enable_anonymous_sign_ins = false

[auth.external.google]
enabled = true
client_id = "your-google-client-id"
secret = "env(SUPABASE_GOOGLE_CLIENT_SECRET)"
# Redirect URI should be configured in Google Cloud Console
# Example: https://127.0.0.1:3000/oauth/callback
# For production, use: https://your-domain.com/oauth/callback
```

**JWT Settings:**
- Default expiry: `jwt_expiry = 3600` (1 hour)
- Refresh token rotation: enabled by default
- Service role key: stored securely (not in config.toml)

**Email testing (Inbucket):**
```toml
[inbucket]
enabled = true
port = 54324
```
Access email UI at: `http://localhost:54324`

---

## 5. Environment Variables

### Backend Required Variables

```bash
# Supabase credentials
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Database (local Supabase)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=documents
MINIO_SECURE=false

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5173/oauth/callback
APP_URL=http://localhost:5173
OAUTH_AUTO_REGISTER=true
```

### Frontend Required Variables

```bash
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=http://127.0.0.1:54321
VITE_SUPABASE_ANON_KEY=your-anon-key-here
```

### Where to Get Keys

1. **Supabase Dashboard (remote):**
   - Go to **Settings → API**
   - Copy `Project URL` (SUPABASE_URL)
   - Copy `anon` public key (SUPABASE_ANON_KEY)
   - Copy `service_role` secret key (SUPABASE_SERVICE_ROLE_KEY)

2. **Local Supabase:**
   - Run `supabase status` to see connection details
   - Keys are generated automatically on first `supabase start`

3. **Google OAuth:**
   - Create credentials in [Google Cloud Console](https://console.cloud.google.com)
   - Set Authorized redirect URI: `https://127.0.0.1:3000/oauth/callback` (local)
   - Or: `http://localhost:5173/oauth/callback` (frontend port)
   - Set `client_secret` in backend `.env` file
   - Set `client_id` in backend `.env` file

---

## 6. Testing Flow — Local Development Workflow

### Step-by-Step Workflow

**Prerequisites:**
- Node.js installed
- Docker Desktop running
- Supabase CLI installed: `npm install -g supabase`

**1. Initialize Supabase:**
```bash
supabase init
```
Creates `supabase/` directory with `config.toml`

**2. Configure Google OAuth (if using):**
- Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in backend `.env`
- Configure redirect URI in Google Cloud Console
- Update `supabase/config.toml`:
  ```toml
  [auth.external.google]
  enabled = true
  client_id = "your-client-id"
  secret = "env(SUPABASE_GOOGLE_CLIENT_SECRET)"
  ```

**3. Start Supabase local stack:**
```bash
supabase start
```
Starts all containers (Postgres, GoTrue, Studio, etc.)

**4. Verify services:**
```bash
supabase status
```
Shows all running containers and URLs:
- API URL: http://127.0.0.1:54321
- DB URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres
- Studio URL: http://127.0.0.1:54323

**5. Apply migrations:**
```bash
supabase db push
```

**6. Start Docker Compose (Redis, MinIO, backend, frontend, Celery):**
```bash
cd docker
docker compose up -d
```

**7. Apply migrations to backend database:**
```bash
cd backend
uv run alembic upgrade head
# OR
pytest tests/
```

**8. Start backend locally (if not using Docker):**
```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**9. Start frontend locally (if not using Docker):**
```bash
cd frontend
npm run dev
```
Frontend runs on http://localhost:5173

**10. Verify workflow:**
- Access Supabase Studio: http://localhost:54323
- Check tables in `public` schema
- Access MinIO console: http://localhost:9001
- Start backend: http://localhost:8000/docs
- Start frontend: http://localhost:5173

### Shutting Down

**Stop Supabase:**
```bash
supabase stop
```

**Stop Docker Compose:**
```bash
cd docker
docker compose down
```

**Clean all data (destructive):**
```bash
supabase db reset
docker compose down -v
```
(Use `-v` to remove volumes too)

### Development Workflow Tips

1. **Hot reload:**
   - Backend: `uvicorn app.main:app --reload`
   - Frontend: `npm run dev`
   - Supabase Studio: auto-reloads on config changes

2. **View logs:**
   - Supabase: `supabase logs`
   - Docker: `docker compose logs -f [service_name]`

3. **Debug migrations:**
   - Check diff: `supabase db diff`
   - View migration files: `supabase migration list`
   - Reset DB: `supabase db reset`

4. **Database access:**
   - Connect via Studio: http://localhost:54323
   - Or psql: `psql postgresql://postgres:postgres@127.0.0.1:54322/postgres`

5. **Email testing:**
   - Check Inbucket UI: http://localhost:54324
   - View emails sent during development

6. **Google OAuth issues on localhost:**
   - Use `https://127.0.0.1:3000` or `http://localhost:5173` in redirect URIs
   - Don't use `localhost` without port (Chrome blocks OAuth on :80 and :443)

---

## Unresolved Questions

1. **Migration tool selection:** Should we use Supabase CLI migrations (`supabase db push`) or Alembic migrations? The docs show both options. Alembic might be better for custom Python ORM migrations.

2. **Google OAuth redirect URI:** Should we use frontend port (5173) or backend port (3000) for redirect URI? Current config uses 3000, but frontend runs on 5173 in Vite.

3. **Celery with asyncpg:** Does Celery worker work with `postgresql+asyncpg` connection string, or should we use synchronous driver for Celery? Need to test.

4. **Database backup strategy:** How to backup local Supabase PostgreSQL database? Standard pg_dump or Supabase CLI backup?

5. **Database seeding:** Should we use `supabase/seed.sql` for development data, or have separate test seed scripts? Current config loads seed.sql on reset.

6. **Environment variable exposure:** Should we store Google Client Secret as environment variable `SUPABASE_GOOGLE_CLIENT_SECRET` or just use `GOOGLE_CLIENT_SECRET`? Current config.toml uses `env(SUPABASE_GOOGLE_CLIENT_SECRET)`.

7. **Testing in CI:** What should CI pipeline do with Supabase? Run `supabase start` ephemeral database, apply migrations, run tests, then destroy? Current docs suggest this approach.

---

## Sources

- [Supabase CLI GitHub](https://github.com/supabase/cli)
- [Supabase CLI Quick Start](https://supabase.com/docs/guides/cli/quickstart)
- [Supabase Local Development](https://supabase.com/docs/guides/cli/local-development)
- [Supabase CLI Configuration](https://supabase.com/docs/guides/cli/configuring-the-cli)
- [Supabase Environment Variables](https://supabase.com/docs/guides/guides/cli/environment-variables)
- [Supabase Client Keys Explained](https://supabase.com/docs/guides/api/getting-started)
- [Google OAuth with Supabase](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [Supabase DB Push Reference](https://supabase.com/docs/reference/cli/supabase-db-push)
- [Docker Compose Project Structure](https://stackoverflow.com/questions/65479859/supabase-environment-variables)
