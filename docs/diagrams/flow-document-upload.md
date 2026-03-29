# Document Upload Flow

> Source: [system-architecture.md](../system-architecture.md) - Data Flow Diagrams

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend (Vue.js)
    participant API as FastAPI Backend
    participant MinIO as MinIO Storage
    participant DB as PostgreSQL
    participant Celery as Celery Worker
    participant OpenAI as OpenAI API
    participant WS as WebSocket

    User->>FE: Select file to upload
    FE->>FE: Validate file type & size

    FE->>API: POST /api/v1/documents/upload<br/>(FormData + JWT token)
    API->>API: Validate JWT token
    API->>API: Check RBAC permissions

    API->>MinIO: Upload file to /documents/{filename}
    MinIO-->>API: file_path confirmed

    API->>DB: INSERT document record<br/>(status: pending)
    DB-->>API: document_id

    API->>Celery: Dispatch process_document task
    API-->>FE: 202 Accepted (document_id)

    Note over Celery: Async Processing Begins

    Celery->>MinIO: Download file
    MinIO-->>Celery: File content

    Celery->>Celery: Parse document<br/>(PyPDF2 / python-docx / openpyxl)
    Celery->>Celery: Chunk text<br/>(500 chars, 50 overlap)
    Celery->>DB: UPDATE document SET status = 'processing'

    loop For each chunk
        Celery->>OpenAI: Generate embedding<br/>(text-embedding-3-small)
        OpenAI-->>Celery: 1536-dim vector
        Celery->>DB: INSERT document_chunk<br/>(content + embedding)
    end

    Celery->>DB: UPDATE document SET status = 'completed'

    Celery->>WS: Notify status change
    WS-->>FE: WebSocket message (completed)
    FE-->>User: Success notification
```

## Flow Summary

| Step | Component | Action |
|------|-----------|--------|
| 1 | Frontend | User selects file, validates type (PDF/DOCX/XLSX) & size (<50MB) |
| 2 | API | Validates JWT, checks RBAC (editor/admin role required) |
| 3 | API | Uploads file to MinIO, creates DB record (status: pending) |
| 4 | API | Dispatches Celery task, returns 202 Accepted |
| 5 | Celery | Downloads file from MinIO, parses text content |
| 6 | Celery | Chunks text (500 chars, 50 overlap), generates embeddings via OpenAI |
| 7 | Celery | Saves chunks with embeddings to pgvector column |
| 8 | WebSocket | Notifies frontend of completion status |
