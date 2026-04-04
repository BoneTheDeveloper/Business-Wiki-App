# Tech Stack - RAG Business Document Wiki

**Last Updated:** 2026-04-04
**Status:** Confirmed for MVP

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                              │
│  Vue.js 3 + Vite + TypeScript + PrimeVue + Tailwind CSS     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API LAYER                                 │
│  FastAPI + Supabase Auth (JWKS RS256) + RBAC               │
│  WebSocket for real-time updates                            │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Document        │ │    RAG           │ │   Task Queue     │
│  Service         │ │  Pipeline        │ │   (Celery)       │
│  Upload/Parse    │ │  Chunk/Embed     │ │   Async Proc     │
└──────────────────┘ └──────────────────┘ └──────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  MinIO           │ │  PostgreSQL      │ │    Redis         │
│  Object Storage  │ │  + pgvector      │ │    Cache/Queue   │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

## Confirmed Stack

### Frontend
| Component | Technology | Version |
|-----------|------------|---------|
| Framework | Vue.js 3 (Composition API) | ^3.4 |
| Build Tool | Vite | ^5.0 |
| Language | TypeScript | ^5.0 |
| State Management | Pinia | ^2.1 |
| Routing | Vue Router | ^4.2 |
| UI Components | PrimeVue | ^3.49 |
| Styling | Tailwind CSS | ^3.4 |
| HTTP Client | Axios | ^1.6 |
| Utilities | VueUse | ^10.7 |

### Backend
| Component | Technology | Version |
|-----------|------------|---------|
| Framework | FastAPI | ^0.115.0 |
| Language | Python | ^3.11 |
| Package Manager | uv | - |
| ASGI Server | Uvicorn | ^0.34.0 |
| ORM | SQLAlchemy | ^2.0.38 |
| Validation | Pydantic | ^2.10.0 |
| Auth | Supabase Auth (JWKS RS256) | - |
| Task Queue | Celery | ^5.4.0 |
| Vector DB | pgvector | ^0.4.0 |
| Object Storage | MinIO | ^7.2.15 |
| LLM API | Google Gemini (google-genai) | ^1.0.0 |
| RAG | LangChain | ^0.3.0 |

### Data Layer
| Component | Technology | Version |
|-----------|------------|---------|
| Database | PostgreSQL | ^15 with pgvector |
| Cache/Queue | Redis | ^7.2 |
| Object Storage | MinIO | ^7.2.15 |
| Containerization | Docker + Compose | Latest |

### Document Processing
| Task | Library |
|------|---------|
| PDF Parsing | PyPDF2 + pdfplumber |
| DOCX Parsing | python-docx |
| XLSX Parsing | openpyxl |

### RAG Pipeline
| Task | Library |
|------|---------|
| Chunking | LangChain RecursiveCharacterTextSplitter |
| Embeddings | Google Gemini (gemini-embedding-001, 1536 dims) |
| Orchestration | LangChain |
| Response Gen | Google Gemini (gemini-2.0-flash) |

### Infrastructure
| Component | Technology |
|-----------|------------|
| Containerization | Docker + Docker Compose |
| Reverse Proxy | Nginx |
| Monitoring | (Phase 2) Prometheus + Grafana |

## Database Schema (Core)

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    format VARCHAR(20),
    status VARCHAR(50) DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Document Chunks (with vectors)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id),
    content TEXT NOT NULL,
    embedding vector(1536),  -- Gemini embedding dims
    chunk_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

## API Structure

```
/api/v1
├── /auth
│   ├── POST /login
│   ├── POST /register
│   └── POST /refresh
├── /documents
│   ├── GET /
│   ├── POST /upload
│   ├── GET /{id}
│   ├── DELETE /{id}
│   └── GET /{id}/status
├── /search
│   └── POST /query
├── /chat
│   └── POST /message
├── /admin
│   ├── GET /users
│   └── GET /stats
└── /ws
    └── /document/{id}
```

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/wiki_db

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Google Gemini
GOOGLE_API_KEY=your-google-api-key
GEMINI_CHAT_MODEL=gemini-2.0-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

## Deployment Targets

| Environment | Config |
|-------------|--------|
| Development | Docker Compose (local) |
| Staging | Docker Compose (VPS) |
| Production | Docker Compose + Nginx (self-hosted) |

## MVP Scope (2-3 weeks)

### In Scope
- User auth (register, login, JWT)
- Document upload (PDF, DOCX, XLSX)
- Document parsing & chunking
- Vector embedding (Google Gemini)
- Semantic search
- Basic chat with RAG
- Admin dashboard (user management)

### Out of Scope (Phase 2+)
- Reranking
- Local embeddings
- PaddleOCR
- Mobile app
- Advanced analytics
- Multi-tenancy

---

**Decision Rationale:**
- **Vue.js 3** over React: User preference, Composition API better for TypeScript
- **FastAPI** over Django: Async-first, better for real-time features
- **pgvector** over Qdrant: Simpler stack, PostgreSQL already needed for metadata
- **MinIO** over S3: Self-hosted, S3-compatible API
- **Google Gemini** for embeddings + chat: Free tier available, fast inference, migrate to local later if needed
