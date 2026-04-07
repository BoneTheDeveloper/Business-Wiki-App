# Documentation Hub — RAG Business Document Wiki

**Last Updated:** 2026-04-04

## File Tree

```
docs/
├── CLAUDE.md                          ← You are here (agent context + navigation)
│
├── project-management/
│   └── project-overview-pdr.md        ← Product requirements & scope
│
├── architecture/
│   ├── overview.md                    ← High-level system diagram (Mermaid)
│   ├── system-architecture.md         ← Full system design & components
│   ├── deployment.md                  ← Deployment architecture diagrams
│   └── database-er-schema.md          ← ER diagram & schema
│
├── api/
│   └── api-docs.md                    ← All endpoints, auth flow, request/response examples
│
├── flows/
│   ├── authentication-authorization.md
│   ├── document-upload.md
│   ├── rag-pipeline.md
│   ├── rag-chat.md
│   └── semantic-search.md
│
├── context/
│   ├── tech-stack.md                  ← Technology choices & versions
│   ├── multi-tenant.md                ← Multi-tenancy design (planned)
│   └── env-vars.md                    ← Environment variable reference
│
├── conventions/
│   └── code-standards.md              ← Coding conventions & patterns
│
├── ops/
│   ├── roadmap.md                     ← Project roadmap, phases, milestones, timeline
│   ├── deployment-guide.md            ← Dev/staging/prod deployment procedures
│   └── supabase-local-to-production.md
│
├── design/
│   └── design-guidelines.md           ← UI/UX guidelines
│
└── testing/
    ├── auto.md                       ← Automated: test pyramid, commands, CI pipeline
    └── manual.md                      ← Manual: curl commands, smoke checklist, endpoint testing
```

## Quick Navigation

| Want to... | Read |
|---|---|
| Understand the product | `project-management/project-overview-pdr.md` |
| See roadmap & phases | `ops/roadmap.md` |
| System at a glance | `architecture/overview.md` |
| Full system design | `architecture/system-architecture.md` |
| Tech choices & versions | `context/tech-stack.md` |
| Env vars | `context/env-vars.md` |
| Multi-tenancy plans | `context/multi-tenant.md` |
| Auth flow | `flows/authentication-authorization.md` |
| All API endpoints | `api/api-docs.md` |
| Coding conventions | `conventions/code-standards.md` |
| Deploy the app | `ops/deployment-guide.md` |
| UI/UX guidelines | `design/design-guidelines.md` |
| Test strategy & commands | `testing/auto.md` |
| Manual testing guide | `testing/manual.md` |
| Supabase pipeline | `ops/supabase-local-to-production.md` |

---

## Agent Context (for AI assistants)

### Stack at a Glance

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Vue.js 3 (Composition API) + TypeScript | ^3.4 |
| UI Kit | PrimeVue + Tailwind CSS | ^3.49 / ^3.4 |
| Build | Vite | ^5.0 |
| State | Pinia | ^2.1 |
| HTTP | Axios | ^1.6 |
| Backend | FastAPI + Pydantic | ^0.115 / ^2.10 |
| Python | 3.11+ | - |
| ORM | SQLAlchemy | ^2.0 |
| Task Queue | Celery + Redis | ^5.4 / ^7.2 |
| Database | PostgreSQL + pgvector | ^15 / ^0.4 |
| Storage | MinIO | ^7.2 |
| Auth | Supabase Auth (PKCE OAuth) | - |
| AI | Google Gemini (gemini-2.0-flash, gemini-embedding-001) | ^1.0 (google-genai) |
| RAG | LangChain | ^0.3 |
| Pkg Mgmt | uv (backend) / pnpm (frontend) | - |

### Dev Commands

```bash
# Docker (recommended for local dev)
docker-compose up -d                    # Start all services
docker-compose logs -f backend          # View backend logs
docker-compose down                     # Stop all services

# Backend local
cd backend
uv sync                                 # Install deps
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend local
cd frontend
pnpm install                            # Install deps
pnpm dev                                # Dev server (localhost:5173)

# Linting
cd frontend && pnpm lint                # Frontend lint
cd backend && uv run ruff check .       # Backend lint

# Testing
cd backend && uv run pytest tests/ -v                    # Backend tests (SQLite mode)
TEST_USE_DOCKER=true uv run pytest tests/ -v             # Backend tests (real PG + pgvector)
uv run pytest tests/ -v --cov=app --cov-report=term-missing  # Backend with coverage
cd frontend && pnpm test                # Frontend tests (Vitest — Phase 6+)

# Supabase local
supabase start                          # Start local Supabase
supabase db reset                       # Reset local DB + run migrations
supabase migration new <name>           # Create new migration
```

### Key Ports

| Service | Port |
|---------|------|
| Frontend | 5173 |
| Backend API | 8000 |
| Chainlit Playground | 8001 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| MinIO API | 9000 |
| MinIO Console | 9001 |
| Supabase (local) | 54321 |

### Architecture Rules

- **Auth:** Supabase Auth handles all auth. Frontend uses PKCE OAuth flow. Backend validates JWT from Supabase.
- **API prefix:** All backend endpoints under `/api/v1/`
- **Database:** PostgreSQL with pgvector for embeddings. Migrations via Supabase CLI.
- **File storage:** MinIO (S3-compatible). Never store uploads in filesystem.
- **Async processing:** Celery tasks for document parsing, embedding generation.
- **Vector search:** pgvector with IVFFlat index, cosine similarity, top-10 results.
- **Chunking:** 500 chars, 50 overlap via LangChain RecursiveCharacterTextSplitter.

### Testing Rules

- **Auth mocking:** Use `app.dependency_overrides[get_current_user]` — never real Supabase calls in tests
- **DB modes:** SQLite in-memory (default, no Docker) or Testcontainers PG (`TEST_USE_DOCKER=true`)
- **pgvector tests:** Mark `@pytest.mark.pgvector`, auto-skipped without Docker
- **Test isolation:** Per-test `drop_all` + `create_all` for clean DB state
- **Frontend tests:** Vitest + happy-dom + `vi.mock` for API client (Phase 6+)
- **E2E:** Playwright with `@smoke` tagged tests for PR, full suite nightly (Phase 8+)
- **Coverage gate:** `--cov-fail-under=50` once Phase 5 completes
- **See:** `docs/testing/auto/README.md` for automated test pyramid, `docs/testing/manual/README.md` for manual testing guide

### Anti-Patterns (DO NOT)

- **Do NOT** create CLAUDE.md files in subdirectories — one at `docs/CLAUDE.md` is enough
- **Do NOT** duplicate docs across directories — single source of truth per topic
- **Do NOT** store secrets in code — use `.env` files (gitignored)
- **Do NOT** skip Supabase Auth — all authenticated endpoints require JWT validation
- **Do NOT** use mock data in tests — test against real services where possible
- **Do NOT** create new doc files without checking if topic is already covered

### Multi-tenant Rules

- Current: single-tenant (one org per deployment)
- Planned: multi-tenant via Supabase RLS (Row Level Security)
- See `context/multi-tenant.md` for design decisions
- Write all new DB queries with future tenant_id filtering in mind

### Mermaid Workflow

When creating or editing Mermaid diagrams in docs:

1. **Generate** diagram syntax
2. **Validate** via MCP tool `validate_and_render_mermaid_diagram`
3. **Fix** parse errors → re-validate until pass
4. **Write** to file only after validation passes

Rules:
- Use Mermaid v11 syntax (call `/mermaidjs-v11` skill for reference)
- No deprecated syntax (`->>`, old class diagram syntax, etc.)
- Keep diagrams under 50 nodes for readability
- Prefer `flowchart` over `graph` (v11 best practice)

---

## For New Developers

1. `project-management/project-overview-pdr.md` — Product goals
2. `architecture/overview.md` — System at a glance
3. `context/tech-stack.md` — Technology stack & versions
4. `api/api-docs.md` — API endpoints & auth flow
5. `conventions/code-standards.md` — Coding conventions
