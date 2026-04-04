"""Tests for chat endpoints."""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_chat_no_documents(auth_client: AsyncClient):
    """Test chat when no documents found — returns fallback message."""
    with patch("app.api.v1.routes.chat.rag_service") as mock_rag:
        mock_rag.search = AsyncMock(return_value=[])

        response = await auth_client.post(
            "/api/v1/chat",
            json={"query": "What is the policy?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["sources"] == []


@pytest.mark.asyncio
async def test_chat_short_query(auth_client: AsyncClient):
    """Test chat with too short query returns 400."""
    response = await auth_client.post(
        "/api/v1/chat",
        json={"query": "hi"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chat_without_auth(client: AsyncClient):
    """Test chat requires authentication."""
    response = await client.post(
        "/api/v1/chat",
        json={"query": "test question"}
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_chat_with_history(auth_client: AsyncClient):
    """Test chat with conversation history."""
    with patch("app.api.v1.routes.chat.rag_service") as mock_rag, \
         patch("app.api.v1.routes.chat.llm_service") as mock_llm:
        mock_rag.search = AsyncMock(return_value=[
            {
                "chunk_id": "test-chunk",
                "content": "Testing is important for quality.",
                "metadata": {},
                "document_id": "doc-123",
                "filename": "test.pdf",
                "format": "pdf",
                "similarity": 0.85
            }
        ])
        mock_llm.chat = AsyncMock(return_value={
            "answer": "Testing is important for software quality.",
            "sources": [],
            "model": "gemini-2.0-flash",
            "usage": {"prompt_tokens": 15, "completion_tokens": 25}
        })

        response = await auth_client.post(
            "/api/v1/chat",
            json={
                "query": "What about testing?",
                "conversation_history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"}
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
