# Database Entity-Relationship Diagram

> Source: [system-architecture.md](../system-architecture.md), [tech-stack.md](../tech-stack.md)

```mermaid
erDiagram
    users {
        UUID id PK
        VARCHAR(255) email UK
        VARCHAR(255) password_hash
        VARCHAR(50) role "user / editor / admin"
        BOOLEAN is_active
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }

    documents {
        UUID id PK
        UUID user_id FK
        VARCHAR(255) filename
        VARCHAR(500) file_path
        INTEGER file_size
        VARCHAR(20) format "pdf / docx / xlsx"
        VARCHAR(50) status "pending / processing / completed / failed"
        JSONB doc_metadata
        TEXT extracted_text
        TEXT error_message
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }

    document_chunks {
        UUID id PK
        UUID document_id FK
        TEXT content
        VECTOR(1536) embedding
        INTEGER chunk_index
        JSONB chunk_metadata
        TIMESTAMP created_at
    }

    users ||--o{ documents : "owns"
    documents ||--o{ document_chunks : "has (cascade delete)"

    users {
        note1: "idx_users_email ON (email)"
    }
    documents {
        note1: "idx_documents_user_id ON (user_id)"
    }
    document_chunks {
        note1: "idx_chunks_document_id ON (document_id)"
        note2: "idx_chunks_embedding ON (embedding) USING ivfflat"
    }
```

## Schema Details

### users
- **id**: UUID primary key, auto-generated
- **email**: Unique, indexed for fast lookup
- **password_hash**: bcrypt with 12 salt rounds
- **role**: Enum - `user` (read-only), `editor` (upload/edit/delete own), `admin` (manage all)

### documents
- **user_id**: FK to users, cascade on delete
- **status**: `pending` -> `processing` -> `completed` | `failed`
- **doc_metadata**: JSONB for flexible metadata (page count, word count, etc.)
- **file_size**: In bytes

### document_chunks
- **embedding**: pgvector column, 1536 dimensions (OpenAI text-embedding-3-small)
- **chunk_index**: Sequential index for ordering within document
- **chunk_metadata**: JSONB (page number, file position, etc.)
- **IVFFlat index** for fast cosine similarity search (100 lists)
