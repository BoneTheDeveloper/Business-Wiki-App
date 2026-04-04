# RAG Business Document Wiki - Product Overview & Requirements

**Project:** RAG Business Document Wiki
**Version:** 0.1.0 (MVP)
**Last Updated:** 2026-03-27

## Executive Summary

RAG Business Document Wiki is a vector-based document management and Q&A platform that enables businesses to upload, store, and query documents using semantic search and conversational AI. The application combines document processing, vector embeddings, and large language models to provide intelligent document retrieval and chat capabilities.

## Business Value

**Problem Solved:**
- Manual document searching across multiple files is time-consuming and error-prone
- Teams waste hours searching for specific information in scattered documents
- Traditional keyword search misses semantic meaning and context

**Solution Provided:**
- Upload documents once, query them anytime
- Semantic search understands context, not just keywords
- Chat interface with document sources
- Role-based access control for sensitive business documents

**Target Users:**
- Knowledge workers (research, compliance, legal)
- Customer support teams
- Small-to-medium businesses

## Functional Requirements

### Core Features

#### 1. User Management
- **FR-001:** User registration and authentication
  - Email/password registration
  - Password strength validation
  - Email verification (planned for Phase 2)

- **FR-002:** JWT-based authentication
  - Login endpoint with email/password
  - Token refresh mechanism
  - Token expiration (30 minutes)

- **FR-003:** Role-based access control (RBAC)
  - User (read-only): View and search documents
  - Editor: Upload, edit, delete own documents
  - Admin: Manage users, view all documents

#### 2. Document Management
- **FR-004:** Document upload
  - Support PDF, DOCX, XLSX formats
  - File size limit: 50MB per file
  - Chunk size: 500 characters, overlap: 50 characters
  - Maximum 1000 chunks per document

- **FR-005:** Document parsing
  - Extract text content from uploaded files
  - Preserve structure (headers, paragraphs)
  - Handle malformed files gracefully

- **FR-006:** Document storage
  - Store original files in MinIO object storage
  - Store parsed text chunks in PostgreSQL
  - Store embeddings in pgvector column

- **FR-007:** Document deletion
  - Users can delete own documents
  - Admins can delete any document
  - Cascade delete chunks and embeddings

#### 3. Semantic Search
- **FR-008:** Query interface
  - Natural language query input
  - Retrieve top 10 relevant chunks
  - Return document context and relevance score

- **FR-009:** Search results display
  - Document name and filename
  - Highlighted matching context
  - Relevance score (0-100%)
  - Source page number (estimated)

#### 4. Document Chat (RAG)
- **FR-010:** Conversational interface
  - Chat with uploaded documents
  - Context-aware responses based on retrieved chunks
  - Source citations for each response (RAG)

- **FR-011:** Chat context management
  - Keep conversation history (last 5 messages)
  - Retrieve relevant chunks for each message
  - Build RAG prompt with retrieved context
  - Use Google Gemini gemini-2.0-flash for chat responses

### Non-Functional Requirements

#### Performance Requirements
- **NFR-001:** Document upload < 5 seconds for files < 10MB
- **NFR-002:** Search query response < 1 second
- **NFR-003:** Chat response < 3 seconds
- **NFR-004:** Page load < 2 seconds

#### Scalability Requirements
- **NFR-005:** Support 1000 concurrent users
- **NFR-006:** Process 100 documents/hour
- **NFR-007:** Store 100,000 documents (Phase 2)

#### Reliability Requirements
- **NFR-008:** 99.5% uptime (target for production)
- **NFR-009:** Data persistence guarantee
- **NFR-010:** Backup and recovery procedures

#### Security Requirements
- **NFR-011:** JWT tokens signed with RS256 (Supabase Auth)
- **NFR-012:** Passwords hashed with bcrypt
- **NFR-013:** Role-based access enforced at API level
- **NFR-014:** CORS configured for allowed origins only
- **NFR-015:** Sensitive data (API keys, passwords) never logged

#### Availability Requirements
- **NFR-016:** Document processing status real-time updates
- **NFR-017:** WebSocket support for live status
- **NFR-018:** Error notifications for processing failures

## Technical Constraints

### Development Constraints
- Use Python 3.11+ for backend
- Use Vue 3 Composition API for frontend
- Maintain consistency with existing codebase
- Follow established coding standards (see `docs/development/code-standards.md`)

### Integration Constraints
- PostgreSQL with pgvector extension for embeddings
- Redis for caching and Celery broker
- MinIO for object storage (S3-compatible)
- Google Gemini API for embeddings and LLM

### Deployment Constraints
- Docker Compose for development and staging
- Self-hosted for production
- Support for custom domain

## MVP Scope (2-3 Weeks)

### In Scope
- User auth (register, login, JWT)
- Document upload (PDF, DOCX, XLSX)
- Document parsing & chunking
- Vector embedding (Google Gemini gemini-embedding-001)
- Semantic search with relevance scores
- Basic chat with RAG
- Admin dashboard (user management, document stats)
- WebSocket real-time updates

### Out of Scope (Phase 2+)
- Email verification
- Advanced OCR (PaddleOCR)
- Local embeddings (sentence-transformers)
- Document versioning
- Advanced analytics and reporting
- Multi-tenancy
- Mobile application
- API rate limiting
- Advanced security features (2FA, audit logs)

## Success Criteria

### MVP Acceptance Criteria
- Users can register, login, and upload documents
- Documents are processed asynchronously via Celery
- Users can search documents and see relevance scores
- Users can chat with documents and get cited responses
- Admins can view all users and documents
- Real-time status updates work via WebSocket

### Performance Metrics
- Document upload: < 5 seconds (10MB file)
- Search query: < 1 second
- Chat response: < 3 seconds
- 100 concurrent users with < 2s response time

### Quality Metrics
- Zero critical bugs
- < 10% error rate
- Code coverage > 60%
- Documentation completeness > 90%

## Architecture Overview

### High-Level Design

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
│  FastAPI + JWT Auth + RBAC + WebSocket                       │
│  (backend/app/)                                              │
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

### Database Schema

**Users Table**
- id (UUID, primary key)
- email (unique, indexed)
- password_hash (bcrypt)
- role (enum: user/editor/admin)
- is_active (boolean)
- created_at, updated_at (timestamps)

**Documents Table**
- id (UUID, primary key)
- user_id (FK to users, indexed)
- filename (string)
- file_path (string)
- file_size (integer)
- format (enum: pdf/docx/xlsx)
- status (enum: pending/processing/completed/failed)
- doc_metadata (JSONB)
- extracted_text (text)
- error_message (text)
- created_at, updated_at (timestamps)

**DocumentChunks Table**
- id (UUID, primary key)
- document_id (FK to documents, indexed, cascade delete)
- content (text)
- embedding (vector(1536))
- chunk_index (integer)
- chunk_metadata (JSONB)
- created_at (timestamp)

## Risk Assessment

### Technical Risks

**Risk 1: Document Processing Complexity**
- **Description:** Complex parsing for various document formats
- **Mitigation:** Use proven libraries (PyPDF2, pdfplumber), implement retry logic
- **Contingency:** Reduce supported formats to MVP (PDF only)

**Risk 2: Embedding Costs**
- **Description:** Google Gemini API costs for embeddings
- **Mitigation:** Use gemini-embedding-001 (cheaper), implement rate limiting
- **Contingency:** Switch to local embeddings in Phase 2

**Risk 3: Vector Database Performance**
- **Description:** pgvector may slow down with large embeddings
- **Mitigation:** Use IVFFlat index, limit results to top 10 chunks
- **Contingency:** Migrate to dedicated vector DB (Qdrant) in Phase 2

### Operational Risks

**Risk 4: API Key Security**
- **Description:** Google Gemini API key exposure
- **Mitigation:** Store in environment variables, rotate regularly
- **Contingency:** Use proxy server for API calls

**Risk 5: Data Privacy**
- **Description:** Document content may contain sensitive information
- **Mitigation:** RBAC, audit logging, data retention policies
- **Contingency:** Implement encryption at rest

## Dependencies

### Internal Dependencies
- Existing backend (FastAPI) - Phase 1
- Existing frontend (Vue 3) - Phase 1
- Existing Docker infrastructure - Phase 1

### External Dependencies
- Google Gemini API (embeddings + chat) - Monthly subscription
- PostgreSQL with pgvector extension - Self-hosted or managed
- Redis - Self-hosted or managed
- MinIO - Self-hosted (Docker)

## Version History

### Version 0.1.0 (MVP - March 2026)
- Initial release
- User auth (JWT)
- Document upload & parsing
- Semantic search
- Chat with RAG
- Admin dashboard
- WebSocket real-time updates

### Version 0.2.0 (Phase 2 - Q2 2026)
- Email verification
- Local embeddings
- OCR support
- Advanced search filters
- API rate limiting

### Version 1.0.0 (GA - Q3 2026)
- Production-ready features
- Advanced analytics
- Multi-tenancy
- Mobile-responsive design

## Glossary

- **RAG:** Retrieval-Augmented Generation - combines search with LLM responses
- **Vector Embedding:** Numerical representation of text meaning
- **pgvector:** PostgreSQL extension for vector similarity search
- **Chunk:** Extracted text segment from document (500 chars)
- **Celery:** Distributed task queue for async processing
- **MinIO:** S3-compatible object storage

## Contacts

**Product Owner:** TBD
**Tech Lead:** TBD
**Development Team:** TBD
