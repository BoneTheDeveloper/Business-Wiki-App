# System Architecture - RAG Business Document Wiki

**Last Updated:** 2026-04-04
**Version:** 0.1.0

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                              │
│  Vue.js 3 + Vite + TypeScript + PrimeVue + Tailwind CSS     │
│  (frontend/src/)                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API LAYER                                 │
│  FastAPI + Supabase Auth + RBAC + WebSocket                  │
│  (backend/app/)                                              │
│  - API Routes (auth, documents, search, chat, admin)         │
│  - Supabase JWT Verification (JWKS RS256)                    │
│  - Role-Based Access Control                                │
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
│  (minio_service) │ │  (models)        │ │   (celery_tasks) │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

## Components

### 1. Frontend Layer (Vue.js 3)

**Tech Stack:**
- Vue 3 (Composition API)
- TypeScript 5.3
- Vite 5.0
- Pinia (State Management)
- Vue Router 4.2
- PrimeVue 3.49
- Tailwind CSS 3.4

**Architecture Pattern:** Component-Based with Composition API

**Core Components:**

**Views** (`src/views/`)
- `Dashboard.vue` - User overview with stats and recent activity
- `Chat.vue` - RAG chat interface with source citations
- `Search.vue` - Semantic search with relevance scores
- `DocumentDetail.vue` - Document viewer and metadata
- `Login.vue` - Authentication form
- `Register.vue` - Registration form
- `Admin.vue` - Admin dashboard with user management

**Stores** (`src/stores/`)
- `auth-store.ts` - Authentication state (user, token, role)
- `document-store.ts` - Document state with WebSocket integration

**Composables** (`src/composables/`)
- `use-web-socket.ts` - WebSocket connection and status updates

**API Layer** (`src/api/`)
- `client.ts` - Axios HTTP client with interceptors

**Features:**
- Reactive data binding
- Protected routes with role-based access
- Real-time status updates via WebSocket
- Form validation
- Error handling with toast notifications

### 2. Backend Layer (FastAPI)

**Tech Stack:**
- Python 3.11
- FastAPI 0.115.0
- SQLAlchemy 2.0.38
- Pydantic 2.10.0
- Supabase Auth (JWKS RS256 verification)
- Google Gemini AI 1.0.0
- Celery 5.4.0
- LangChain 0.3.0
- pgvector 0.4.0

**Architecture Pattern:** RESTful API with Async Processing

**Core Modules:**

**API Layer** (`app/api/v1/routes/`)
- `documents.py` - Document CRUD operations
- `search.py` - Semantic search with vector embeddings
- `chat.py` - RAG chat endpoint
- `admin.py` - Admin endpoints (user management, stats)
- `websocket.py` - WebSocket for real-time updates
- `auth/routes.py` - Authentication endpoint (GET /auth/me only)
- `auth/supabase.py` - JWKS token verification

**Data Layer** (`app/models/`)
- `models.py` - SQLAlchemy ORM models (User, Document, DocumentChunk)
- `schemas.py` - Pydantic schemas for requests/responses
- `database.py` - Database initialization and connection

**Business Logic** (`app/services/`)
- `rag_service.py` - RAG pipeline orchestration
- `celery_tasks.py` - Async task processing
- `llm_service.py` - Google Gemini embeddings and chat
- `minio_service.py` - S3-compatible storage operations
- `parsing.py` - Document parsing (PDF/DOCX/XLSX)

**Utilities** (`app/utils/`)
- `websocket.py` - WebSocket utilities

**Key Patterns:**
- Dependency Injection for auth and database sessions
- Async/await for I/O operations
- Celery for long-running tasks
- JWT-based authentication
- Role-based access control

### 3. Data Layer

**PostgreSQL + pgvector**

**Tables:**

**users** (5 columns)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**documents** (12 columns)
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    format VARCHAR(20),
    status VARCHAR(50) DEFAULT 'pending',
    doc_metadata JSONB DEFAULT '{}',
    extracted_text TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**document_chunks** (7 columns)
```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    chunk_index INTEGER NOT NULL,
    chunk_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vector index for fast similarity search
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Indexes:**
- `idx_users_email` on users(email)
- `idx_documents_user_id` on documents(user_id)
- `idx_chunks_document_id` on document_chunks(document_id)
- `idx_chunks_embedding` on document_chunks(embedding)

**Redis**

**Purpose:**
- Celery task broker and result backend
- Session caching (planned for Phase 2)
- Rate limiting (planned for Phase 2)

**Configuration:**
- Redis URL: `redis://localhost:6379/0`
- Used by: Celery workers, FastAPI application

**MinIO**

**Purpose:** S3-compatible object storage for documents

**Configuration:**
- Endpoint: `minio:9000` (internal Docker network)
- Access Key: `minioadmin`
- Secret Key: `minioadmin`
- Bucket: `documents`

**Usage:**
- Store original uploaded files
- Provide file download endpoint
- Serve files via CDN (planned for Phase 2)

### 4. RAG Pipeline

**Flow:**

```
User Upload → Parse → Chunk → Embed → Store → Search/Chat
```

**Step 1: Document Parsing**
- **Library:** PyPDF2, pdfplumber (PDF), python-docx (DOCX), openpyxl (XLSX)
- **Process:**
  - Extract text content from file
  - Preserve structure (headers, paragraphs)
  - Handle malformed files gracefully

**Step 2: Text Chunking**
- **Library:** LangChain RecursiveCharacterTextSplitter
- **Parameters:**
  - Chunk size: 500 characters
  - Chunk overlap: 50 characters
  - Preserve paragraphs
- **Output:** List of text chunks with metadata

**Step 3: Embedding Generation**
- **Model:** Google Gemini gemini-embedding-001
- **Dimensions:** 1536
- **Process:**
  - Split text into batches (max 1000 chars)
  - Call Google Gemini embeddings API
  - Store vectors in pgvector column

**Step 4: Storage**
- Save chunks to `document_chunks` table
- Associate with parent document
- Store metadata (page number, file position)

**Step 5: Search/Query**
- Convert user query to embedding
- Query pgvector with cosine similarity
- Return top 10 most relevant chunks

**Step 6: Response Generation**
- Build RAG prompt with retrieved context
- Call Google Gemini chat API
- Return response with source citations

## API Endpoints

### Authentication
```
POST   /api/v1/auth/login         User login
POST   /api/v1/auth/register      User registration
POST   /api/v1/auth/refresh       Refresh JWT token
```

### Documents
```
GET    /api/v1/documents          List user documents
POST   /api/v1/documents/upload   Upload document
GET    /api/v1/documents/{id}     Get document details
DELETE /api/v1/documents/{id}     Delete document
GET    /api/v1/documents/{id}/status  Processing status
```

### Search
```
POST   /api/v1/search/query       Semantic search
```

### Chat
```
POST   /api/v1/chat/message       RAG chat
```

### Admin (admin only)
```
GET    /api/v1/admin/users        List all users
GET    /api/v1/admin/stats        Get stats
```

### WebSocket
```
WS     /ws/documents              Document status updates
```

### Playground (RAG Testing — local dev only, requires `PLAYGROUND_ENABLED=true`)
```
POST   /api/v1/playground/chat      Chat with detailed RAG step info
POST   /api/v1/playground/search    Search with chunk details + scores
GET    /api/v1/playground/documents List available docs (no auth)
```

**Backend Playground Endpoints:**

**POST /api/v1/playground/chat**
- Request: `{ "message": "User query", "chat_history": [] }`
- Response: `{ "response": "AI answer", "steps": [...], "latency_ms": 1234, "retrieved_chunks": [...] }`
- Purpose: Chat with RAG pipeline, shows retrieval steps, latency metrics, similarity scores
- Auth: No (gated by PLAYGROUND_ENABLED env var)
- Connects to: Chainlit RAG Playground via httpx async client

**POST /api/v1/playground/search**
- Request: `{ "query": "Search query", "top_k": 10 }`
- Response: `{ "results": [...], "latency_ms": 234, "chunks_with_scores": [...] }`
- Purpose: Search with detailed chunk retrieval and similarity scores
- Auth: No (gated by PLAYGROUND_ENABLED env var)
- Connects to: Chainlit RAG Playground via httpx async client

**GET /api/v1/playground/documents**
- Request: `GET /playground/documents`
- Response: `{ "documents": [{"id": "...", "filename": "...", "chunk_count": 42}, ...] }`
- Purpose: List available documents for playground testing
- Auth: No (gated by PLAYGROUND_ENABLED env var)
- Connects to: Chainlit RAG Playground via httpx async client

**Chainlit RAG Playground:**
- Tech Stack: Chainlit 1.0+ (web UI for RAG pipeline debugging)
- Port: 8001
- Docker Profile: "playground" (enabled by default when PLAYGROUND_ENABLED=true)
- Auth: No JWT auth (open access when enabled)
- Features: Visual RAG pipeline steps, latency metrics, retrieved chunks with similarity scores
- Data Flow: Chainlit → httpx async client → Backend playground endpoints → RAG service → Database → Response with detailed metrics

## Data Flow Diagrams

### Document Upload Flow

```
1. Frontend: User selects file → FormData
2. Backend (POST /upload):
   - Validate auth token
   - Upload to MinIO → /documents/{filename}
   - Create Document record (status: pending)
   - Dispatch Celery task (process_document)
3. Celery Worker:
   - Download from MinIO
   - Parse text (parsing.py)
   - Chunk text (RecursiveCharacterTextSplitter)
   - Generate embeddings (llm_service.py)
   - Save chunks to PostgreSQL (document_chunks)
   - Update Document status (status: completed)
4. WebSocket:
   - Backend notifies frontend of status change
5. Frontend:
   - Receive WebSocket message
   - Update document-store
   - Show success notification
```

### Semantic Search Flow

```
1. Frontend: User types query → POST /search/query
2. Backend:
   - Validate auth token
   - Get user ID from token
   - Generate query embedding (llm_service.py)
   - Query pgvector with cosine similarity
   - Return top 10 chunks with relevance scores
3. Frontend:
   - Display results in card format
   - Highlight matching context
   - Show relevance score (0-100%)
```

### RAG Chat Flow

```
1. Frontend: User sends message → POST /chat/message
2. Backend:
   - Validate auth token
   - Get user ID and message
   - Generate query embedding
   - Search for relevant chunks (top 10)
   - Build RAG prompt with context
   - Call Google Gemini chat API
   - Return response with citations
3. Frontend:
   - Display AI response
   - Show source citations
   - Append to chat history
```

## Security Architecture

### Authentication Flow

```
1. User clicks "Sign in with Google" → Supabase OAuth (PKCE)
2. Supabase Auth handles Google consent + token exchange
3. Frontend receives session (access_token, refresh_token)
4. Subsequent requests include token in Authorization header
5. Backend verifies JWT via Supabase JWKS (RS256)
6. Auto-refresh handled by Supabase client SDK
```

### Authorization Flow

```
1. Route decorator checks user role
2. Example: @require_role('admin')
3. If user.role != 'admin', return 403 Forbidden
4. Admin-only endpoints:
   - GET /api/v1/admin/users
   - GET /api/v1/admin/stats
   - DELETE /api/v1/documents/{id} (admin only)
```

### Security Measures

**Authentication:**
- Supabase Auth with JWKS RS256 verification
- Google OAuth (PKCE flow) via Supabase client SDK
- Token refresh handled automatically by Supabase SDK
- Token expiration managed by Supabase

**Authorization:**
- Role-based access control (user/editor/admin)
- Endpoint-level protection
- Resource ownership validation

**Data Protection:**
- HTTPS required in production
- CORS restricted to allowed origins
- No sensitive data logged
- Database queries parameterized (SQL injection protection)

**Input Validation:**
- Pydantic schemas for all requests
- Email format validation
- File size limits
- File type validation

## Scalability Considerations

### Current Scalability

**Supported Load:**
- 1000 concurrent users
- 100 documents/hour processing
- 100,000 documents stored (Phase 2)

**Performance Targets:**
- Upload: < 5 seconds (10MB file)
- Search: < 1 second
- Chat: < 3 seconds

### Scalability Enhancements (Phase 2+)

**Horizontal Scaling:**
- Load balancer (Nginx) for multiple backend instances
- Database read replicas for search
- CDN for static assets

**Performance Optimization:**
- Redis caching for frequent queries
- Document search index optimization
- Async processing with queue scaling

**Data Management:**
- Document versioning
- Archive old documents
- Database partitioning for large datasets

**Infrastructure:**
- Kubernetes for container orchestration
- Managed PostgreSQL and Redis
- Auto-scaling workers

## Deployment Architecture

### Development (Docker Compose)

```
┌─────────────────────────────────────────────────────────────┐
│                   Docker Compose Services                    │
├─────────────────────────────────────────────────────────────┤
│  postgres: pgvector/pgvector:pg15                            │
│  redis: redis:7.2-alpine                                     │
│  minio: minio/minio:latest                                   │
│  backend: FastAPI (binds to :8000)                           │
│  frontend: Vite dev server (binds to :5173)                  │
│  celery_worker: Celery worker                                │
│  chainlit: RAG Playground (binds to :8001)                   │
└─────────────────────────────────────────────────────────────┘
```

**Environment:**
- Development mode with hot reload
- Volumes for code persistence
- Health checks for services

### Production

**Recommended Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                   Production Deployment                      │
├─────────────────────────────────────────────────────────────┤
│  Load Balancer (Nginx)                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Backend 1  │  │  Backend 2  │  │  Backend 3  │       │
│  │ (FastAPI)    │  │ (FastAPI)    │  │ (FastAPI)    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│           │           │           │                          │
│  ┌────────▼───────────▼───────────▼──────────┐               │
│  │  PostgreSQL (primary + replicas)           │               │
│  └─────────────────────────────────────────────┘               │
│  ┌─────────────────────────────────────────────┐               │
│  │  Redis (cluster)                            │               │
│  └─────────────────────────────────────────────┘               │
│  ┌─────────────────────────────────────────────┐               │
│  │  MinIO (object storage)                     │               │
│  └─────────────────────────────────────────────┘               │
│  ┌─────────────────────────────────────────────┐               │
│  │  Celery Workers (multiple instances)        │               │
│  └─────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

**Environment Variables:**
- `DATABASE_URL` - Production database connection
- `REDIS_URL` - Production Redis connection
- `MINIO_ENDPOINT` - Production MinIO endpoint
- `GOOGLE_API_KEY` - Google Gemini API key
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key
- `CELERY_BROKER_URL` - Production Redis URL
- `PLAYGROUND_ENABLED` - Enable playground endpoints (default: false, no JWT auth)
- `CHAINLIT_PORT` - Chainlit playground port (default: 8001)

## Monitoring & Observability

### Health Checks
- `/health` endpoint for service health
- Database connection checks
- MinIO connectivity checks

### Logging
- Application logs (structlog or python-logging)
- Error logs with stack traces
- Access logs for monitoring

### Metrics (Phase 2)
- Document upload rate
- Search query frequency
- Processing time by document size
- Error rates

### Tracing (Phase 2)
- Distributed tracing for async tasks
- Request-response correlation IDs

## Backup & Recovery

### Database Backups
- Daily automated backups
- Point-in-time recovery
- Backup retention: 30 days

### Object Storage Backups
- MinIO replication to secondary region (Phase 2)

### Disaster Recovery
- Database failover procedures
- Service restart procedures
- Rollback procedures for updates

## Error Handling

### API Errors
- 400 Bad Request - Validation errors
- 401 Unauthorized - Invalid/expired token
- 403 Forbidden - Insufficient permissions
- 404 Not Found - Resource not found
- 500 Internal Server Error - Unexpected errors

### Document Processing Errors
- Parse errors logged with details
- Failed documents marked with status: 'failed'
- Error message stored in database
- Frontend notified via WebSocket

### WebSocket Errors
- Auto-reconnect logic
- Error notifications
- Connection status display
