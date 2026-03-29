# RAG Business Document Wiki - Implementation Plan

**Created:** 2026-03-26
**Timeline:** 2-3 weeks MVP
**Mode:** Auto-approved

## Overview

Build a RAG-powered document wiki with Vue.js frontend and FastAPI backend. Users can upload documents (PDF/DOCX/XLSX), which are parsed, chunked, embedded, and made searchable via semantic search and chat interface.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Vue.js 3 Frontend (Vite + TypeScript + PrimeVue)           │
│  Port: 5173                                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Backend (Python 3.11 + SQLAlchemy + Pydantic)      │
│  Port: 8000                                                 │
│  • JWT Auth + RBAC                                          │
│  • REST API + WebSocket                                     │
│  • Rate Limiting                                            │
└─────────────────────────────────────────────────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  PostgreSQL 15   │ │  Redis           │ │  MinIO           │
│  + pgvector      │ │  Port: 6379      │ │  Port: 9000      │
│  Port: 5432      │ │  Celery Broker   │ │  Object Storage  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

## Phase Summary

| # | Phase | Duration | Key Deliverables |
|---|-------|----------|------------------|
| 1 | Project Setup | 1 day | Docker Compose, project structure, dev environment |
| 2 | Database & Auth | 2 days | PostgreSQL schema, pgvector, JWT auth, RBAC |
| 3 | Document Service | 3 days | Upload, MinIO integration, parsing (PDF/DOCX/XLSX) |
| 4 | RAG Pipeline | 3 days | Chunking, embeddings, pgvector search, Celery tasks |
| 5 | Frontend Core | 3 days | Vue setup, auth, document upload, list/view |
| 6 | Chat & Search | 3 days | Chat interface, semantic search, WebSocket status |
| 7 | Admin Dashboard | 2 days | User management, stats, queue monitoring |
| 8 | Testing & Polish | 2 days | Tests, error handling, documentation |

**Total:** ~18 days (2.5 weeks)

## Phase Files

- [Phase 01 - Project Setup](./phase-01-project-setup.md)
- [Phase 02 - Database & Auth](./phase-02-database-auth.md)
- [Phase 03 - Document Service](./phase-03-document-service.md)
- [Phase 04 - RAG Pipeline](./phase-04-rag-pipeline.md)
- [Phase 05 - Frontend Core](./phase-05-frontend-core.md)
- [Phase 06 - Chat & Search](./phase-06-chat-search.md)
- [Phase 07 - Admin Dashboard](./phase-07-admin-dashboard.md)
- [Phase 08 - Testing & Polish](./phase-08-testing-polish.md)

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Vector DB | pgvector | Simpler stack, PostgreSQL already needed |
| Embeddings (MVP) | OpenAI text-embedding-3-small | Fastest to implement, migrate to local later |
| Chunking | LangChain RecursiveCharacterTextSplitter | Battle-tested, configurable |
| Task Queue | Celery + Redis | Proven pattern, good FastAPI integration |
| Frontend State | Pinia | Official Vue 3 recommendation |
| UI Components | PrimeVue | Full-featured, good TypeScript support |

## MVP Scope

### ✅ In Scope
- User registration, login, JWT refresh
- Document upload (drag-drop, progress)
- PDF/DOCX/XLSX parsing with metadata extraction
- Text chunking (512 tokens, 50 overlap)
- Vector embeddings via OpenAI
- Semantic search with relevance scores
- Chat with RAG (context from retrieved chunks)
- Admin: user list, document stats, queue status
- WebSocket: real-time processing status

### ❌ Out of Scope (Phase 2)
- Reranking
- Local embeddings
- PaddleOCR for scanned PDFs
- Mobile app
- Document versioning
- Multi-tenancy
- Advanced analytics

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| OpenAI API limits | Add retry logic, queue requests |
| Large file uploads | Chunked upload, progress tracking |
| Processing failures | Celery retry, error logging, user notification |
| pgvector performance | IVFFlat index, tune `lists` parameter |
| Memory issues | Chunked processing, streaming responses |

## Success Criteria

1. User can upload PDF/DOCX/XLSX and see processing status in real-time
2. Semantic search returns relevant results with highlighted context
3. Chat answers include source citations with page numbers
4. Admin can view all users and system stats
5. All tests pass, no critical security issues
