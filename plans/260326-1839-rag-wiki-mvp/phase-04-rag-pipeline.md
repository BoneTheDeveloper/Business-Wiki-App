# Phase 04 - RAG Pipeline

**Priority:** P0 | **Duration:** 3 days | **Status:** Pending

## Overview

Implement RAG pipeline: text chunking, OpenAI embeddings, pgvector storage, and semantic search.

## Key Insights

- LangChain RecursiveCharacterTextSplitter (512 tokens, 50 overlap)
- OpenAI text-embedding-3-small (1536 dimensions)
- pgvector IVFFlat index for similarity search
- Top-K retrieval with metadata filtering

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG Pipeline Flow                         │
├─────────────────────────────────────────────────────────────┤
│  Document Text                                               │
│       ↓                                                      │
│  Chunk (512 tokens, 50 overlap)                             │
│       ↓                                                      │
│  Embed (OpenAI text-embedding-3-small)                      │
│       ↓                                                      │
│  Store (pgvector)                                           │
│       ↓                                                      │
│  Query → Vector Search → Top-K Results                      │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

### Functional
- Chunk text with metadata preservation
- Generate embeddings via OpenAI API
- Store vectors in pgvector
- Semantic search with cosine similarity
- Filter by document_id, format, date range

### Non-Functional
- Embedding generation: < 2s per chunk
- Vector search: < 500ms for Top-20
- Batch embedding for efficiency

## Related Files

**Create:**
- `backend/app/services/rag_service.py` - RAG orchestration
- `backend/app/api/v1/routes/search.py` - Search endpoints

## Implementation Steps

### 1. RAG Service

```python
# backend/app/services/rag_service.py
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pgvector.sqlalchemy import Vector
import numpy as np
from app.config import settings
from app.models.models import DocumentChunk, Document

class RAGService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.embed_model = "text-embedding-3-small"
        self.embed_dimensions = 1536
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            length_function=lambda x: len(x.split()),
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict]:
        """Split text into chunks with metadata"""
        chunks = self.splitter.split_text(text)
        return [
            {
                "content": chunk,
                "metadata": {
                    **(metadata or {}),
                    "chunk_index": i,
                    "word_count": len(chunk.split())
                }
            }
            for i, chunk in enumerate(chunks)
        ]

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        response = await self.client.embeddings.create(
            model=self.embed_model,
            input=text,
            dimensions=self.embed_dimensions
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batch)"""
        response = await self.client.embeddings.create(
            model=self.embed_model,
            input=texts,
            dimensions=self.embed_dimensions
        )
        return [item.embedding for item in response.data]

    async def search(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 10,
        document_ids: Optional[List[str]] = None,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Semantic search with optional filters"""
        # Embed query
        query_embedding = await self.embed(query)

        # Build SQL with vector search
        sql = """
            SELECT
                dc.id,
                dc.content,
                dc.metadata,
                dc.document_id,
                d.filename,
                d.format,
                1 - (dc.embedding <=> :embedding) as similarity
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE d.status = 'completed'
        """
        params = {"embedding": str(query_embedding)}

        # Add filters
        if document_ids:
            sql += " AND dc.document_id = ANY(:doc_ids)"
            params["doc_ids"] = document_ids

        if filters:
            if filters.get("format"):
                sql += " AND d.format = :format"
                params["format"] = filters["format"]

        # Order by similarity and limit
        sql += f" ORDER BY dc.embedding <=> :embedding LIMIT {top_k}"

        result = await db.execute(text(sql), params)
        rows = result.fetchall()

        return [
            {
                "chunk_id": str(row.id),
                "content": row.content,
                "metadata": row.metadata,
                "document_id": str(row.document_id),
                "filename": row.filename,
                "format": row.format,
                "similarity": float(row.similarity)
            }
            for row in rows
        ]

rag_service = RAGService()
```

### 2. Search Routes

```python
# backend/app/api/v1/routes/search.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
from app.models.database import get_db
from app.models.models import User
from app.dependencies import get_current_user
from app.services.rag_service import rag_service

router = APIRouter(prefix="/search", tags=["search"])

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    document_ids: Optional[List[str]] = None
    filters: Optional[dict] = None

class SearchResult(BaseModel):
    chunk_id: str
    content: str
    metadata: dict
    document_id: str
    filename: str
    format: str
    similarity: float

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total: int

@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Semantic search across documents"""
    if not request.query or len(request.query) < 3:
        raise HTTPException(400, "Query must be at least 3 characters")

    results = await rag_service.search(
        db=db,
        query=request.query,
        top_k=min(request.top_k, 20),
        document_ids=request.document_ids,
        filters=request.filters
    )

    return SearchResponse(
        query=request.query,
        results=[SearchResult(**r) for r in results],
        total=len(results)
    )

@router.get("/suggest")
async def suggest(
    q: str = Query(..., min_length=2),
    limit: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Quick search suggestions (prefix match)"""
    # Simple prefix search on document titles
    from sqlalchemy import select, or_
    from app.models.models import Document

    result = await db.execute(
        select(Document.filename)
        .where(
            Document.user_id == current_user.id,
            or_(
                Document.filename.ilike(f"{q}%"),
                Document.filename.ilike(f"%{q}%")
            )
        )
        .limit(limit)
    )
    suggestions = [row[0] for row in result.fetchall()]

    return {"query": q, "suggestions": suggestions}
```

### 3. Vector Index Setup

```python
# Add to backend/app/models/database.py init_db function
async def init_db():
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Create tables
        await conn.run_sync(Base.metadata.create_all)

        # Create IVFFlat index for vector similarity
        # Only create if not exists
        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE indexname = 'idx_chunks_embedding_ivf'
                ) THEN
                    CREATE INDEX idx_chunks_embedding_ivf
                    ON document_chunks
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                END IF;
            END
            $$;
        """))
```

### 4. Update Celery Task for Embeddings

```python
# Update process_document in celery_tasks.py
@shared_task(name="process_document", bind=True)
def process_document(self, document_id: str, file_path: str, format_type: str):
    """Process document: download, parse, chunk, embed"""
    # ... existing parsing code ...

    try:
        # ... parsing ...

        # Chunk and embed (batch)
        rag = RAGService()
        chunks = rag.chunk_text(parsed['text'], doc.metadata)

        # Batch embed for efficiency
        contents = [c['content'] for c in chunks]
        embeddings = await rag.embed_batch(contents)

        # Store chunks
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            db_chunk = DocumentChunk(
                document_id=doc.id,
                content=chunk['content'],
                embedding=embedding,
                chunk_index=i,
                metadata=chunk.get('metadata', {})
            )
            db.add(db_chunk)

        await db.commit()
        # ...
```

## Todo List

- [ ] Create rag_service.py with chunk/embed/search
- [ ] Create search.py routes
- [ ] Update database.py with vector index
- [ ] Update celery_tasks.py for batch embeddings
- [ ] Add OpenAI API key validation
- [ ] Add rate limiting for embeddings
- [ ] Test: Chunk text produces correct overlap
- [ ] Test: Embedding returns 1536-dim vector
- [ ] Test: Search returns relevant results
- [ ] Test: Filters work correctly

## Success Criteria

1. Text chunked into 512-token chunks with 50 overlap
2. Embeddings generated via OpenAI API
3. Vector search returns Top-K with similarity scores
4. Filters (document_id, format) work correctly
5. Search latency < 500ms for Top-20

## Next Steps

- Phase 05: Frontend core (Vue setup, auth, document UI)
