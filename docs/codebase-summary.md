# Codebase Summary - RAG Business Document Wiki

**Last Updated:** 2026-03-27
**Total Lines:** 3,551 (Backend 1,863 + Frontend 1,688)

## Project Structure

```
RAG_Business_Wiki_App/
├── backend/                 # FastAPI backend (1,863 LOC)
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── routes/
│   │   │       │   ├── admin.py          # User management, stats
│   │   │       │   ├── chat.py           # RAG chat endpoint
│   │   │       │   ├── documents.py      # CRUD operations
│   │   │       │   ├── search.py         # Semantic search
│   │   │       │   ├── websocket.py      # Real-time updates
│   │   │       │   └── __init__.py
│   │   │       └── __init__.py
│   │   ├── auth/
│   │   │   ├── routes.py                # Login/register
│   │   │   └── security.py              # JWT, password hashing
│   │   ├── models/
│   │   │   ├── database.py              # DB initialization
│   │   │   ├── models.py                # SQLAlchemy models
│   │   │   └── schemas.py               # Pydantic schemas
│   │   ├── services/
│   │   │   ├── celery_tasks.py          # Async processing
│   │   │   ├── llm_service.py           # OpenAI integration
│   │   │   ├── minio_service.py         # S3-compatible storage
│   │   │   ├── parsing.py               # PDF/DOCX/XLSX parsing
│   │   │   ├── rag_service.py           # RAG pipeline
│   │   │   └── __init__.py
│   │   ├── utils/
│   │   │   └── websocket.py             # WebSocket utilities
│   │   ├── config.py                    # Configuration settings
│   │   ├── dependencies.py              # Dependency injection
│   │   ├── main.py                      # FastAPI app entry
│   │   └── __init__.py
│   ├── tests/
│   │   ├── conftest.py                  # Test fixtures
│   │   ├── test_admin.py
│   │   ├── test_auth.py
│   │   ├── test_chat.py
│   │   ├── test_documents.py
│   │   └── test_search.py
│   ├── pyproject.toml                   # Poetry dependencies
│   └── Dockerfile
├── frontend/                          # Vue.js 3 frontend (1,688 LOC)
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts                # Axios client + interceptors
│   │   ├── components/
│   │   │   └── # (0 files - components in development)
│   │   ├── composables/
│   │   │   └── use-web-socket.ts        # WebSocket composable
│   │   ├── router/
│   │   │   └── index.ts                 # Vue Router setup
│   │   ├── stores/
│   │   │   ├── auth-store.ts            # Pinia auth state
│   │   │   ├── document-store.ts        # Pinia document state
│   │   │   └── index.ts
│   │   ├── views/
│   │   │   ├── Chat.vue                 # RAG chat interface
│   │   │   ├── Dashboard.vue            # User dashboard
│   │   │   ├── DocumentDetail.vue       # Document viewer
│   │   │   ├── Login.vue                # Login page
│   │   │   ├── Register.vue             # Registration page
│   │   │   ├── Search.vue               # Semantic search
│   │   │   └── Admin.vue                # Admin dashboard
│   │   ├── App.vue                      # Root component
│   │   ├── main.ts                      # App entry point
│   │   ├── vite-env.d.ts                # Vite types
│   │   └── styles/                      # Global styles
│   ├── package.json                     # NPM dependencies
│   ├── tsconfig.json                    # TypeScript config
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile.dev
├── docker-compose.yml                  # Multi-service orchestration
├── .env.example                         # Environment variables template
└── README.md                            # Project overview
```

## Backend Architecture

### Core Modules

**API Layer** (`backend/app/api/v1/routes/`)
- **documents.py** (approx. 150 LOC)
  - POST /upload - Multipart upload with Celery task dispatch
  - GET / - List user documents
  - GET /{id} - Get document details
  - DELETE /{id} - Delete document (cascade)
  - GET /{id}/status - Check processing status

- **search.py** (approx. 80 LOC)
  - POST /query - Semantic search with pgvector
  - Returns chunks with relevance scores

- **chat.py** (approx. 100 LOC)
  - POST /message - RAG chat endpoint
  - Retrieves chunks + generates response with LLM

- **admin.py** (approx. 120 LOC)
  - GET /users - List all users (admin only)
  - GET /stats - Document stats overview

- **websocket.py** (approx. 80 LOC)
  - WebSocket connection for real-time status
  - Broadcasts document processing updates

**Authentication** (`backend/app/auth/`)
- **routes.py** (approx. 60 LOC)
  - POST /login - JWT token generation
  - POST /register - User creation with bcrypt hashing

- **security.py** (approx. 40 LOC)
  - create_access_token() - JWT encoding
  - get_password_hash() - bcrypt hashing
  - verify_password() - Password verification

**Models** (`backend/app/models/`)
- **models.py** (76 LOC)
  - User - email, password_hash, role, timestamps
  - Document - filename, file_path, status, metadata
  - DocumentChunk - content, embedding (vector 1536), chunk_index

- **schemas.py** (approx. 120 LOC)
  - Pydantic schemas for API requests/responses
  - Request: LoginRequest, RegisterRequest, SearchRequest, ChatRequest
  - Response: LoginResponse, DocumentResponse, SearchResult, ChatMessage

- **database.py** (approx. 30 LOC)
  - init_db() - Create tables if not exists
  - Uses SQLAlchemy metadata

**Services** (`backend/app/services/`)
- **celery_tasks.py** (approx. 100 LOC)
  - upload_document_task() - Async document processing
  - parsing_task() - Extract text, chunk, embed
  - Error handling with try-catch

- **llm_service.py** (approx. 80 LOC)
  - get_embeddings() - Call OpenAI embeddings API
  - generate_response() - Call OpenAI chat API
  - Streaming support (future)

- **minio_service.py** (approx. 60 LOC)
  - upload_file() - S3-compatible upload
  - get_file() - Download from MinIO
  - delete_file() - Delete from storage

- **parsing.py** (approx. 80 LOC)
  - parse_pdf() - PyPDF2 + pdfplumber
  - parse_docx() - python-docx
  - parse_xlsx() - openpyxl

- **rag_service.py** (approx. 120 LOC)
  - search_documents() - Vector similarity search
  - build_rag_prompt() - Construct LLM prompt with context
  - Format response with citations

### Key Technologies

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | ^3.11 | Runtime |
| FastAPI | ^0.115.0 | Web framework |
| SQLAlchemy | ^2.0.38 | ORM |
| pgvector | ^0.4.0 | Vector storage |
| Redis | ^5.2.0 | Cache + Celery broker |
| Celery | ^5.4.0 | Task queue |
| MinIO | ^7.2.15 | Object storage |
| OpenAI | ^1.68.0 | LLM + embeddings |
| LangChain | ^0.3.0 | RAG orchestration |

## Frontend Architecture

### Core Modules

**State Management** (`src/stores/`)
- **auth-store.ts** (approx. 80 LOC)
  - user state: email, token, role
  - actions: login(), logout(), register()
  - Persisted in localStorage

- **document-store.ts** (approx. 100 LOC)
  - documents list state
  - actions: upload(), delete(), fetchAll()
  - WebSocket integration for real-time updates

**API Layer** (`src/api/`)
- **client.ts** (approx. 50 LOC)
  - Axios instance with base URL
  - Request interceptor: Add JWT token
  - Response interceptor: Handle 401 errors (refresh token)
  - Error handling utility

**Routing** (`src/router/`)
- **index.ts** (approx. 60 LOC)
  - Protected routes (require authentication)
  - Role-based route guards (admin only)
  - Routes: dashboard, chat, search, documents, admin

**Views** (`src/views/`)
- **Dashboard.vue** (approx. 150 LOC)
  - Overview stats: total documents, users, chunks
  - Recent activity feed
  - Performance metrics

- **Chat.vue** (approx. 200 LOC)
  - Chat interface with message bubbles
  - RAG integration with document-store
  - Source citations display
  - Typing indicator animation

- **Search.vue** (approx. 180 LOC)
  - Search input with filters
  - Result cards with relevance scores
  - Highlight matching context

- **DocumentDetail.vue** (approx. 100 LOC)
  - Document metadata display
  - Status indicator (processing/completed/failed)
  - Download link

- **Login.vue** (approx. 120 LOC)
  - Form validation
  - Error handling
  - Redirect after login

- **Register.vue** (approx. 130 LOC)
  - Registration form
  - Password strength indicator
  - Email validation

- **Admin.vue** (approx. 200 LOC)
  - User table with role management
  - Document stats
  - User management actions

**Composables** (`src/composables/`)
- **use-web-socket.ts** (approx. 80 LOC)
  - WebSocket connection management
  - Reconnect logic
  - Event handlers for document status updates

### Key Technologies

| Component | Version | Purpose |
|-----------|---------|---------|
| Vue | ^3.4.0 | UI framework |
| TypeScript | ^5.3.3 | Type safety |
| Vite | ^5.0.11 | Build tool |
| Pinia | ^2.1.7 | State management |
| PrimeVue | ^3.49.0 | UI components |
| Axios | ^1.6.5 | HTTP client |
| VueUse | ^10.7.2 | Composables |
| Tailwind CSS | ^3.4.1 | Styling |

## Data Flow

### Document Upload Flow

1. **Frontend** (`frontend/src/views/Dashboard.vue`)
   - User selects file → FormData
   - POST /api/v1/documents/upload
   - Receive document ID

2. **Backend** (`backend/app/api/v1/routes/documents.py`)
   - Validate user auth (JWT)
   - Upload to MinIO
   - Create Document record (status: pending)
   - Dispatch Celery task

3. **Celery Worker** (`backend/app/services/celery_tasks.py`)
   - Download from MinIO
   - Parse text (parsing.py)
   - Chunk text (RecursiveCharacterTextSplitter)
   - Generate embeddings (llm_service.py)
   - Save chunks to PostgreSQL

4. **WebSocket** (`backend/app/api/v1/routes/websocket.py`)
   - Notify frontend of status change

5. **Frontend** (`frontend/src/composables/use-web-socket.ts`)
   - Receive WebSocket message
   - Update document-store
   - Show progress indicator

### Search Flow

1. **Frontend** (`frontend/src/views/Search.vue`)
   - User types query → SearchRequest
   - POST /api/v1/search/query

2. **Backend** (`backend/app/api/v1/routes/search.py`)
   - Get user ID from JWT
   - Query pgvector with cosine similarity
   - Return top 10 chunks with scores

3. **Frontend** (`frontend/src/stores/document-store.ts`)
   - Display results in card format
   - Highlight matching context
   - Show relevance score

### Chat Flow

1. **Frontend** (`frontend/src/views/Chat.vue`)
   - User sends message → ChatRequest
   - POST /api/v1/chat/message

2. **Backend** (`backend/app/api/v1/routes/chat.py`)
   - Get user ID, message
   - Search for relevant chunks (search.py)
   - Build RAG prompt with context
   - Call OpenAI chat API
   - Return response with citations

3. **Frontend**
   - Display AI response
   - Show source citations
   - Append to chat history

## Configuration

### Environment Variables

```env
# Database
DB_USER=wiki
DB_PASSWORD=wiki_secret
DB_NAME=wiki_db

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# OpenAI
OPENAI_API_KEY=sk-xxx

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### Docker Services

- **postgres** (pgvector/pgvector:pg15) - Database
- **redis** (redis:7.2-alpine) - Cache + broker
- **minio** (minio/minio:latest) - Object storage
- **backend** - FastAPI app
- **frontend** - Vue.js dev server
- **celery_worker** - Async task processor

## Code Statistics

### Backend
- **Total Lines:** 1,863
- **API Routes:** 5 endpoints
- **Models:** 3 tables
- **Services:** 5 services
- **Tests:** 5 test files
- **Core Files:**
  - main.py: 64 lines
  - models.py: 76 lines
  - database.py: 30 lines
  - config.py: 40 lines

### Frontend
- **Total Lines:** 1,688
- **Views:** 7 views
- **Stores:** 2 stores
- **Composables:** 1 composable
- **Core Files:**
  - main.ts: 30 lines
  - App.vue: 80 lines
  - router/index.ts: 60 lines
  - api/client.ts: 50 lines

## Key Patterns

### Backend
- **Dependency Injection:** FastAPI dependency functions for auth, database sessions
- **Async Processing:** Celery tasks for long-running operations
- **Error Handling:** Try-catch blocks with error messages
- **JWT Auth:** Token-based auth with role checking
- **WebSocket:** Real-time status updates

### Frontend
- **Composition API:** Vue 3 Composition API for all components
- **Pinia Stores:** Centralized state management
- **TypeScript:** Full type safety
- **Reactive Data:** Vue reactivity system
- **Axios Interceptors:** Centralized API error handling

## Database Schema

### Tables

**users** (5 columns)
- id: UUID (PK)
- email: VARCHAR(255) (unique, indexed)
- password_hash: VARCHAR(255)
- role: ENUM (user/editor/admin)
- is_active: BOOLEAN
- created_at, updated_at: TIMESTAMP

**documents** (12 columns)
- id: UUID (PK)
- user_id: UUID (FK, indexed)
- filename: VARCHAR(255)
- file_path: VARCHAR(500)
- file_size: INTEGER
- format: VARCHAR(20)
- status: ENUM (pending/processing/completed/failed)
- doc_metadata: JSONB
- extracted_text: TEXT
- error_message: TEXT
- created_at, updated_at: TIMESTAMP

**document_chunks** (7 columns)
- id: UUID (PK)
- document_id: UUID (FK, indexed, cascade delete)
- content: TEXT
- embedding: VECTOR(1536)
- chunk_index: INTEGER
- chunk_metadata: JSONB
- created_at: TIMESTAMP

**Indexes:**
- idx_users_email: ON users(email)
- idx_documents_user_id: ON documents(user_id)
- idx_chunks_document_id: ON document_chunks(document_id)
- idx_chunks_embedding: ON document_chunks USING ivfflat (embedding vector_cosine_ops)

## API Endpoints

### Authentication
- POST /api/v1/auth/login - User login
- POST /api/v1/auth/register - User registration

### Documents
- GET /api/v1/documents - List user documents
- POST /api/v1/documents/upload - Upload document
- GET /api/v1/documents/{id} - Get document details
- DELETE /api/v1/documents/{id} - Delete document
- GET /api/v1/documents/{id}/status - Check processing status

### Search
- POST /api/v1/search/query - Semantic search

### Chat
- POST /api/v1/chat/message - RAG chat

### Admin (admin only)
- GET /api/v1/admin/users - List all users
- GET /api/v1/admin/stats - Get stats

### WebSocket
- WS /ws/documents - Document status updates

## Testing

### Backend Tests
- **test_auth.py** - Authentication flows
- **test_documents.py** - CRUD operations
- **test_search.py** - Vector search
- **test_chat.py** - RAG chat
- **test_admin.py** - Admin endpoints

### Test Strategy
- pytest for unit tests
- pytest-asyncio for async tests
- Mock external dependencies (OpenAI, MinIO, Celery)

## Known Issues

1. **Document Processing Time:** Large files (>10MB) may take >5 seconds to process
2. **Token Limits:** OpenAI chat API has 4k context limit (may need reranking in Phase 2)
3. **Vector Search:** pgvector performance degrades with >10k documents (consider migration in Phase 2)

## Future Enhancements

### Phase 2
- Email verification
- Local embeddings (sentence-transformers)
- OCR support (PaddleOCR)
- Advanced search filters
- API rate limiting
- Audit logging

### Phase 3+
- Document versioning
- Multi-tenancy
- Advanced analytics
- Mobile app
- Dark mode
- Custom embedding models
