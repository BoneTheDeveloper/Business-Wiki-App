"""Tests for chat endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_no_documents(client: AsyncClient, auth_headers):
    """Test chat when no documents exist."""
    response = await client.post(
        "/api/v1/chat",
        json={"query": "What is the policy?"},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    # Should indicate no documents found
    assert data["sources"] == []


@pytest.mark.asyncio
async def test_chat_short_query(client: AsyncClient, auth_headers):
    """Test chat with too short query."""
    response = await client.post(
        "/api/v1/chat",
        json={"query": "hi"},
        headers=auth_headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chat_without_auth(client: AsyncClient):
    """Test chat requires authentication."""
    response = await client.post(
        "/api/v1/chat",
        json={"query": "test question"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_with_history(client: AsyncClient, auth_headers):
    """Test chat with conversation history."""
    response = await client.post(
        "/api/v1/chat",
        json={
            "query": "What about testing?",
            "conversation_history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
