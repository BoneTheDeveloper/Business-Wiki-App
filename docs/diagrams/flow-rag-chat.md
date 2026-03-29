# RAG Chat Flow

> Source: [system-architecture.md](../system-architecture.md) - Data Flow Diagrams

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend (Vue.js)
    participant API as FastAPI Backend
    participant OpenAI as OpenAI API
    participant DB as PostgreSQL + pgvector

    User->>FE: Send chat message
    FE->>API: POST /api/v1/chat/message<br/>{ message: "...", history: [...last 5] }

    API->>API: Validate JWT token
    API->>API: Extract user_id

    API->>OpenAI: Generate message embedding<br/>(text-embedding-3-small)
    OpenAI-->>API: 1536-dim vector

    API->>DB: Vector similarity search<br/>Top 10 relevant chunks
    DB-->>API: Retrieved context chunks

    API->>API: Build RAG prompt<br/>[System] + [Context chunks]<br/>+ [Chat history] + [User message]

    API->>OpenAI: Chat completion<br/>(GPT-3.5-turbo)
    OpenAI-->>API: AI response

    API->>API: Format response with citations
    API-->>FE: { response, sources }

    FE->>FE: Display AI response bubble
    FE->>FE: Show source citations
    FE->>FE: Append to chat history
    FE-->>User: Response with citations
```

## RAG Prompt Structure

```
System: You are a document assistant. Answer based only on the provided context.
        If the answer is not in the context, say so.

Context:
[Chunk 1 - Source: report.pdf, Page 3]
[Chunk 2 - Source: policy.docx, Page 1]
... (up to 10 chunks)

History:
User: Previous message 1
Assistant: Previous response 1
... (last 5 messages)

User: Current question
```

## Performance Target

| Metric | Target |
|--------|--------|
| Chat response | < 3 seconds |
| Context chunks | Top 10 |
| History window | Last 5 messages |
| Citation format | Document name + page |
