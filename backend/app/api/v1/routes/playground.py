"""Playground API routes for RAG observability — no auth, gated by PLAYGROUND_ENABLED."""
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import get_db
from app.schemas.playground import (
    PlaygroundSearchRequest,
    PlaygroundSearchResponse,
    PlaygroundChatRequest,
    PlaygroundChatResponse,
    PlaygroundChatSource,
    PlaygroundChunkResult,
    PlaygroundDocumentInfo,
    PlaygroundDocumentsResponse,
    PlaygroundStepsDetail,
    PlaygroundEmbeddingMetrics,
    PlaygroundRetrievalMetrics,
    PlaygroundGenerationMetrics,
)
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service

router = APIRouter(prefix="/playground", tags=["playground"])


def _check_playground_enabled():
    """Raise 403 if playground is not enabled."""
    if not settings.PLAYGROUND_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Playground is disabled. Set PLAYGROUND_ENABLED=true to enable.",
        )


@router.post("/search", response_model=PlaygroundSearchResponse)
async def playground_search(
    request: PlaygroundSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Semantic search with detailed RAG step metrics."""
    _check_playground_enabled()

    if len(request.query.strip()) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")

    start = time.monotonic()

    # Step 1: Embedding — timed separately
    t0 = time.monotonic()
    query_embedding = await rag_service.embed(request.query)
    embed_ms = (time.monotonic() - t0) * 1000

    # Step 2: Retrieval (skip re-embedding by building SQL directly)
    t0 = time.monotonic()
    sql = """
        SELECT
            dc.id, dc.content, dc.chunk_metadata,
            dc.document_id, d.filename, d.format,
            1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.status = 'completed'
    """
    params = {"embedding": str(query_embedding), "limit": min(request.top_k, 50)}

    if request.document_ids:
        sql += " AND dc.document_id = ANY(:doc_ids::uuid[])"
        params["doc_ids"] = request.document_ids

    sql += " ORDER BY dc.embedding <=> CAST(:embedding AS vector) LIMIT :limit"
    result = await db.execute(text(sql), params)
    rows = result.fetchall()
    retrieval_ms = (time.monotonic() - t0) * 1000

    total_ms = (time.monotonic() - start) * 1000

    chunk_results = [
        PlaygroundChunkResult(
            chunk_id=str(row.id),
            content=row.content,
            metadata=row.chunk_metadata or {},
            document_id=str(row.document_id),
            filename=row.filename,
            format=row.format,
            similarity=float(row.similarity),
        )
        for row in rows
    ]

    steps = PlaygroundStepsDetail(
        embedding=PlaygroundEmbeddingMetrics(
            latency_ms=round(embed_ms, 2),
            dimensions=rag_service.embed_dimensions,
        ),
        retrieval=PlaygroundRetrievalMetrics(
            latency_ms=round(retrieval_ms, 2),
            chunks_count=len(rows),
        ),
        generation=PlaygroundGenerationMetrics(
            latency_ms=0, tokens_in=0, tokens_out=0,
        ),
    )

    return PlaygroundSearchResponse(
        query=request.query,
        chunks=chunk_results,
        steps=steps,
        total_latency_ms=round(total_ms, 2),
    )


@router.post("/chat", response_model=PlaygroundChatResponse)
async def playground_chat(
    request: PlaygroundChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Full RAG chat with step-by-step pipeline metrics."""
    _check_playground_enabled()
    start = time.monotonic()

    if len(request.query.strip()) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")

    # Step 1: Embedding
    t0 = time.monotonic()
    query_embedding = await rag_service.embed(request.query)
    embed_ms = (time.monotonic() - t0) * 1000

    # Step 2: Retrieval (reuse embedding, skip re-embedding in rag_service.search)
    t0 = time.monotonic()
    sql = """
        SELECT
            dc.id, dc.content, dc.chunk_metadata,
            dc.document_id, d.filename, d.format,
            1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.status = 'completed'
    """
    params = {"embedding": str(query_embedding), "limit": min(request.top_k, 50)}

    if request.document_ids:
        sql += " AND dc.document_id = ANY(:doc_ids::uuid[])"
        params["doc_ids"] = request.document_ids

    sql += " ORDER BY dc.embedding <=> CAST(:embedding AS vector) LIMIT :limit"
    result = await db.execute(text(sql), params)
    rows = result.fetchall()
    retrieval_ms = (time.monotonic() - t0) * 1000

    # Format chunks
    chunks = [
        {
            "chunk_id": str(row.id),
            "content": row.content,
            "metadata": row.chunk_metadata or {},
            "document_id": str(row.document_id),
            "filename": row.filename,
            "format": row.format,
            "similarity": float(row.similarity),
        }
        for row in rows
    ]

    if not chunks:
        total_ms = (time.monotonic() - start) * 1000
        return PlaygroundChatResponse(
            response="No relevant documents found. Try a different query or upload documents first.",
            chunks=[],
            sources=[],
            steps=PlaygroundStepsDetail(
                embedding=PlaygroundEmbeddingMetrics(
                    latency_ms=round(embed_ms, 2),
                    dimensions=rag_service.embed_dimensions,
                ),
                retrieval=PlaygroundRetrievalMetrics(
                    latency_ms=round(retrieval_ms, 2),
                ),
                generation=PlaygroundGenerationMetrics(latency_ms=0, tokens_in=0, tokens_out=0),
            ),
            model="none",
            total_latency_ms=round(total_ms, 2),
        )

    # Step 3: LLM Generation
    t0 = time.monotonic()
    history = None
    if request.conversation_history:
        history = [
            {"role": m.get("role", "user"), "content": m.get("content", "")}
            for m in request.conversation_history[-4:]
        ]

    llm_result = await llm_service.chat(
        query=request.query,
        context_chunks=chunks,
        conversation_history=history,
    )
    gen_ms = (time.monotonic() - t0) * 1000

    total_ms = (time.monotonic() - start) * 1000

    chunk_results = [
        PlaygroundChunkResult(**c) for c in chunks
    ]

    sources = [
        PlaygroundChatSource(
            document_id=s["document_id"],
            filename=s["filename"],
            chunk_id=s["chunk_id"],
            similarity=s["similarity"],
            page=s.get("page"),
        )
        for s in llm_result.get("sources", [])
    ]

    usage = llm_result.get("usage", {})
    steps = PlaygroundStepsDetail(
        embedding=PlaygroundEmbeddingMetrics(
            latency_ms=round(embed_ms, 2),
            dimensions=rag_service.embed_dimensions,
        ),
        retrieval=PlaygroundRetrievalMetrics(
            latency_ms=round(retrieval_ms, 2),
            chunks_count=len(chunks),
        ),
        generation=PlaygroundGenerationMetrics(
            latency_ms=round(gen_ms, 2),
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
        ),
    )

    return PlaygroundChatResponse(
        response=llm_result.get("answer", ""),
        chunks=chunk_results,
        sources=sources,
        steps=steps,
        model=llm_result.get("model", "unknown"),
        total_latency_ms=round(total_ms, 2),
    )


@router.get("/documents", response_model=PlaygroundDocumentsResponse)
async def playground_documents(
    db: AsyncSession = Depends(get_db),
):
    """List available documents with chunk counts."""
    _check_playground_enabled()

    sql = text("""
        SELECT
            d.id, d.filename, d.format, d.status,
            COUNT(dc.id)::int AS chunk_count
        FROM documents d
        LEFT JOIN document_chunks dc ON dc.document_id = d.id
        WHERE d.status = 'completed'
        GROUP BY d.id, d.filename, d.format, d.status
        ORDER BY d.created_at DESC
    """)
    result = await db.execute(sql)
    rows = result.fetchall()

    documents = [
        PlaygroundDocumentInfo(
            id=str(row.id),
            filename=row.filename,
            format=row.format,
            status=row.status,
            chunk_count=row.chunk_count,
        )
        for row in rows
    ]

    return PlaygroundDocumentsResponse(
        documents=documents,
        total=len(documents),
    )
