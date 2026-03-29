# API Endpoint Structure

> Source: [tech-stack.md](../tech-stack.md), [system-architecture.md](../system-architecture.md)

```mermaid
graph LR
    subgraph V1["/api/v1"]
        subgraph AUTH["/auth"]
            A1["POST /login<br/>User login"]
            A2["POST /register<br/>User registration"]
            A3["POST /refresh<br/>Refresh JWT token"]
        end

        subgraph DOCS["/documents"]
            D1["GET /<br/>List user documents"]
            D2["POST /upload<br/>Upload document"]
            D3["GET /:id<br/>Get document details"]
            D4["DELETE /:id<br/>Delete document"]
            D5["GET /:id/status<br/>Processing status"]
        end

        subgraph SEARCH["/search"]
            S1["POST /query<br/>Semantic search"]
        end

        subgraph CHAT["/chat"]
            C1["POST /message<br/>RAG chat"]
        end

        subgraph ADMIN["/admin"]
            AD1["GET /users<br/>List all users"]
            AD2["GET /stats<br/>System statistics"]
        end

        subgraph WS["/ws"]
            W1["WS /documents<br/>Status updates"]
        end
    end

    classDef auth fill:#dbeafe,stroke:#2563eb,color:#1e40af
    classDef docs fill:#dcfce7,stroke:#16a34a,color:#166534
    classDef search fill:#fef3c7,stroke:#d97706,color:#92400e
    classDef chat fill:#f3e8ff,stroke:#7c3aed,color:#5b21b6
    classDef admin fill:#fee2e2,stroke:#dc2626,color:#991b1b
    classDef ws fill:#e0f2fe,stroke:#0284c7,color:#075985

    class A1,A2,A3 auth
    class D1,D2,D3,D4,D5 docs
    class S1 search
    class C1 chat
    class AD1,AD2 admin
    class W1 ws
```

## Endpoint Details

### Authentication (`/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/login` | None | Login with email/password, returns JWT |
| POST | `/register` | None | Create new user account |
| POST | `/refresh` | JWT | Refresh expired JWT token |

### Documents (`/documents`)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/` | JWT | user+ | List own documents |
| POST | `/upload` | JWT | editor+ | Upload file (PDF/DOCX/XLSX, max 50MB) |
| GET | `/:id` | JWT | owner/admin | Get document metadata |
| DELETE | `/:id` | JWT | owner/admin | Delete document + chunks |
| GET | `/:id/status` | JWT | owner/admin | Get processing status |

### Search (`/search`)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/query` | JWT | user+ | Semantic search, returns top 10 chunks |

### Chat (`/chat`)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/message` | JWT | user+ | RAG chat with source citations |

### Admin (`/admin`)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/users` | JWT | admin | List all users |
| GET | `/stats` | JWT | admin | System-wide statistics |

### WebSocket (`/ws`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| WS | `/documents` | JWT | Real-time document status updates |
