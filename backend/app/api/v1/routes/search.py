"""Search API routes for semantic document search."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Optional, List

from app.models.database import get_db
from app.models.models import User, Document
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.dependencies import get_current_user
from app.services.rag_service import rag_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Semantic search across user's documents.

    Returns top-K most relevant chunks based on vector similarity.
    """
    # Validate query
    if not request.query or len(request.query.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Query must be at least 3 characters"
        )

    # Add user filter to ensure only searching own documents
    filters = request.filters or {}
    filters["user_id"] = str(current_user.id)

    # Perform search
    results = await rag_service.search(
        db=db,
        query=request.query.strip(),
        top_k=min(request.top_k, 20),
        document_ids=request.document_ids,
        filters=filters
    )

    return SearchResponse(
        query=request.query,
        results=[SearchResult(**r) for r in results],
        total=len(results)
    )


@router.get("/suggest")
async def search_suggestions(
    q: str = Query(..., min_length=2, description="Search prefix"),
    limit: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Quick search suggestions based on document filenames.

    Uses prefix matching for autocomplete-style suggestions.
    """
    result = await db.execute(
        select(Document.filename)
        .where(
            Document.user_id == current_user.id,
            Document.status == "completed",
            or_(
                Document.filename.ilike(f"{q}%"),
                Document.filename.ilike(f"%{q}%")
            )
        )
        .distinct()
        .limit(limit)
    )
    suggestions = [row[0] for row in result.fetchall()]

    return {
        "query": q,
        "suggestions": suggestions
    }


@router.get("/documents")
async def search_documents_by_query(
    q: str = Query(..., min_length=3),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search documents by semantic query.

    Returns documents (not chunks) that match the query,
    ordered by best matching chunk similarity.
    """
    # Perform search with higher limit
    results = await rag_service.search(
        db=db,
        query=q,
        top_k=limit * 2,  # Get more to dedupe
        filters={"user_id": str(current_user.id)}
    )

    # Deduplicate by document_id, keeping best match
    seen_docs = {}
    for r in results:
        doc_id = r["document_id"]
        if doc_id not in seen_docs or r["similarity"] > seen_docs[doc_id]["similarity"]:
            seen_docs[doc_id] = r

    # Sort by similarity and limit
    sorted_docs = sorted(
        seen_docs.values(),
        key=lambda x: x["similarity"],
        reverse=True
    )[:limit]

    return {
        "query": q,
        "documents": [
            {
                "id": d["document_id"],
                "filename": d["filename"],
                "format": d["format"],
                "best_similarity": d["similarity"],
                "preview": d["content"][:200] + "..." if len(d["content"]) > 200 else d["content"]
            }
            for d in sorted_docs
        ],
        "total": len(sorted_docs)
    }
