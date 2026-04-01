"""Chat API routes for RAG-powered conversations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.models import User
from app.dependencies import get_current_user
from app.schemas.search import ChatRequest, ChatResponse
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chat with documents using RAG.

    Retrieves relevant chunks and generates response using LLM.
    """
    # Validate query
    if len(request.query.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Query must be at least 3 characters"
        )

    # Retrieve relevant chunks
    chunks = await rag_service.search(
        db=db,
        query=request.query,
        top_k=request.top_k,
        document_ids=request.document_ids,
        filters={"user_id": str(current_user.id)}
    )

    if not chunks:
        return ChatResponse(
            answer="I couldn't find any relevant information in your documents. Please try a different query or upload more documents.",
            sources=[],
            model="none",
            usage={"prompt_tokens": 0, "completion_tokens": 0}
        )

    # Build conversation history
    history = None
    if request.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in request.conversation_history]

    # Generate response
    response = await llm_service.chat(
        query=request.query,
        context_chunks=chunks,
        conversation_history=history
    )

    return ChatResponse(**response)
