# Business Wiki App

A RAG-powered business document wiki that lets you upload, search, and chat with your organization's documents using AI.

## What It Does

- **Document Management** — Upload PDF, DOCX, Excel files. Auto-parsed, chunked, and embedded.
- **Semantic Search** — Natural language search across all documents with relevance scoring.
- **RAG Chat** — Ask questions about your documents. Answers include source citations.
- **Organization & Groups** — Multi-org support with document groups for access control.
- **Playground** — Chainlit-based RAG observability UI for testing and debugging the pipeline.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3, TypeScript, Vite, PrimeVue, Tailwind CSS |
| Backend | FastAPI, Python 3.12, SQLAlchemy, Celery |
| AI/LLM | Google Gemini (embeddings + chat), pgvector |
| Auth | Supabase Auth (Google OAuth) |
| Database | PostgreSQL + pgvector (Supabase managed) |
| Storage | MinIO (S3-compatible) |
| Queue | Redis + Celery |
| Playground | Chainlit |

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/) + Docker Compose
- [Supabase CLI](https://supabase.com/docs/guides/local-development)
- [GNU Make](https://www.gnu.org/software/make/) (Git Bash on Windows includes it via MSYS2)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [pnpm](https://pnpm.io/) (Node package manager)

### Setup

```bash
# 1. Clone and configure
cp .env.example .env.local
# Edit .env.local with your API keys

# 2. Start local Supabase
make supabase

# 3. Install dependencies
make install
```

### Run the App

```bash
# Full stack via Docker (recommended)
make up

# Or run services individually (local dev)
make dev-backend    # Terminal 1
make dev-frontend   # Terminal 2

# Chainlit playground only
make dev-chainlit
```

### All Commands

```
make help
```

| Command | Description |
|---------|-------------|
| `make up` | Start all core services via Docker |
| `make up-playground` | Start all services + Chainlit playground |
| `make dev-backend` | Run backend locally |
| `make dev-frontend` | Run frontend locally |
| `make dev-chainlit` | Run Chainlit playground only |
| `make down` | Stop Docker containers |
| `make logs` | Tail Docker logs |
| `make test` | Run backend tests |
| `make clean` | Remove containers and volumes |

## Project Structure

```
├── backend/          # FastAPI backend + RAG pipeline
├── frontend/         # Vue 3 SPA
├── chainlit/         # RAG playground UI
├── docker/           # Docker Compose config
├── supabase/         # Database migrations
├── docs/             # Full documentation
└── Makefile          # Dev commands
```

## Ports

| Service | Port |
|---------|------|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Chainlit Playground | http://localhost:8001 |
| MinIO Console | http://localhost:9001 |
| Supabase (local) | http://localhost:54321 |

## Documentation

Full documentation is in the [`docs/`](./docs/) directory:

- [Project Requirements](./docs/project-management/project-overview-pdr.md)
- [System Architecture](./docs/architecture/overview.md)
- [API Reference](./docs/api/api-docs.md)
- [Deployment Guide](./docs/ops/deployment-guide.md)
- [Testing Guide](./docs/testing/auto.md)

## License

Private project. All rights reserved.
