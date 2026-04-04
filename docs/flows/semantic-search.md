# Semantic Search Flow

> Source: [system-architecture.md](../system-architecture.md) - Data Flow Diagrams

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend (Vue.js)
    participant API as FastAPI Backend
    participant Gemini as Google Gemini API
    participant DB as PostgreSQL + pgvector

    User->>FE: Type natural language query
    FE->>API: POST /api/v1/search/query<br/>{ query: "...", top_k: 10 }

    API->>API: Validate JWT token
    API->>API: Extract user_id from token

    API->>Gemini: Generate query embedding<br/>(gemini-embedding-001)
    Gemini-->>API: 1536-dim vector

    API->>DB: SELECT chunks with cosine similarity<br/>WHERE user_id matches<br/>ORDER BY embedding <=> query_vector<br/>LIMIT 10
    DB-->>API: Top 10 chunks with scores

    API->>API: Calculate relevance scores (0-100%)
    API-->>FE: Search results with scores

    FE->>FE: Display result cards
    FE-->>User: Show results with<br/>document name, highlighted context,<br/>relevance score, page number
```

## Response Format

```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "content": "...matched text...",
      "relevance_score": 0.92,
      "document": {
        "id": "uuid",
        "filename": "report.pdf"
      },
      "chunk_metadata": {
        "page_number": 3
      }
    }
  ],
  "total": 10,
  "query": "user's search query"
}
```

## Performance Target

| Metric | Target |
|--------|--------|
| Query response | < 1 second |
| Top-K results | 10 chunks |
| Min relevance | No minimum (all returned) |
