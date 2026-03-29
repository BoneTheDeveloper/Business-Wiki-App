# High-Level System Architecture

> Source: [system-architecture.md](../system-architecture.md), [tech-stack.md](../tech-stack.md)

```mermaid
graph TB
    subgraph CLIENT["CLIENT LAYER"]
        FE["Vue.js 3 + Vite + TypeScript<br/>PrimeVue + Tailwind CSS"]
    end

    subgraph API["API LAYER"]
        FASTAPI["FastAPI + JWT Auth + RBAC"]
        WS["WebSocket Server"]
    end

    subgraph SERVICES["SERVICE LAYER"]
        DOC_SVC["Document Service<br/>Upload / Parse"]
        RAG_SVC["RAG Pipeline<br/>Chunk / Embed"]
        TASK_Q["Task Queue<br/>Celery Worker"]
    end

    subgraph DATA["DATA LAYER"]
        PG["PostgreSQL<br/>+ pgvector"]
        REDIS["Redis<br/>Cache / Queue"]
        MINIO["MinIO<br/>Object Storage"]
    end

    subgraph EXTERNAL["EXTERNAL SERVICES"]
        OPENAI["OpenAI API<br/>Embeddings + Chat"]
    end

    FE --> FASTAPI
    FE <--> WS
    FASTAPI --> DOC_SVC
    FASTAPI --> RAG_SVC
    FASTAPI --> TASK_Q
    WS --> FASTAPI

    DOC_SVC --> MINIO
    DOC_SVC --> PG
    RAG_SVC --> PG
    RAG_SVC --> OPENAI
    TASK_Q --> REDIS
    TASK_Q --> PG
    TASK_Q --> MINIO
    TASK_Q --> OPENAI
```

## Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Vue.js Frontend** | UI rendering, state management (Pinia), routing, WebSocket client |
| **FastAPI Backend** | REST API, JWT validation, RBAC enforcement, request routing |
| **WebSocket Server** | Real-time document processing status updates |
| **Document Service** | File upload, parsing (PDF/DOCX/XLSX), MinIO storage |
| **RAG Pipeline** | Text chunking, embedding generation, similarity search, response generation |
| **Celery Worker** | Async document processing, embedding generation |
| **PostgreSQL + pgvector** | Metadata storage, vector similarity search |
| **Redis** | Celery broker, result backend, session cache |
| **MinIO** | S3-compatible document file storage |
| **OpenAI API** | text-embedding-3-small (1536 dims), GPT-3.5-turbo chat |
