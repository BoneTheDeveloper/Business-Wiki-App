# Environment Variables Reference

**Last Updated:** 2026-04-04

## Source of Truth

Root `.env.example` is the single source of truth. Backend and frontend have their own `.env.example` for local dev outside Docker.

## Variable Map

### Root (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_PORT` | Redis port | `6379` |
| `MINIO_API_PORT` | MinIO API port | `9000` |
| `MINIO_CONSOLE_PORT` | MinIO console port | `9001` |
| `BACKEND_PORT` | FastAPI port | `8000` |
| `FRONTEND_PORT` | Vite dev server port | `3000` |
| `SUPABASE_DB_PORT` | Supabase PostgreSQL port | `54322` |
| `SUPABASE_URL` | Supabase API URL | `http://127.0.0.1:54321` |
| `SUPABASE_ANON_KEY` | Supabase anon/public key | — |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | — |
| `GOOGLE_API_KEY` | Google Gemini API key | — |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | — |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | — |
| `MINIO_ACCESS_KEY` | MinIO access key | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO secret key | `minioadmin` |

### Backend (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `MINIO_ENDPOINT` | MinIO endpoint | `localhost:9000` |
| `MINIO_BUCKET` | MinIO bucket name | `documents` |
| `MINIO_SECURE` | Use HTTPS for MinIO | `false` |

### Frontend (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_APP_TITLE` | Browser tab title | `RAG Business Wiki` |
| `VITE_SUPABASE_URL` | Supabase URL (browser) | `http://127.0.0.1:54321` |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key (browser) | — |

## Port Map (Local Dev)

| Service | Port |
|---------|------|
| Vite dev server | 5173 |
| Backend API | 8000 |
| Supabase API | 54321 |
| Supabase DB | 54322 |
| Redis | 6379 |
| MinIO API | 9000 |
| MinIO Console | 9001 |

## Docker vs Local

- **Docker Compose**: reads root `.env` only, passes vars to containers
- **Local dev (no Docker)**: each service reads its own `.env` file
- Keep all 3 `.env` files in sync when developing locally
