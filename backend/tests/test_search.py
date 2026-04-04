"""Tests for search endpoints."""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_search_empty_query(auth_client: AsyncClient):
    """Test search with empty query returns 400."""
    response = await auth_client.post(
        "/api/v1/search",
        json={"query": ""},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_search_too_short(auth_client: AsyncClient):
    """Test search with too short query returns 400."""
    response = await auth_client.post(
        "/api/v1/search",
        json={"query": "ab"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_search_no_documents(auth_client: AsyncClient):
    """Test search when no documents exist."""
    with patch("app.api.v1.routes.search.rag_service") as mock_rag:
        mock_rag.search = AsyncMock(return_value=[])

        response = await auth_client.post(
            "/api/v1/search",
            json={"query": "test query"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["total"] == 0


@pytest.mark.asyncio
async def test_search_without_auth(client: AsyncClient):
    """Test search requires authentication."""
    response = await client.post(
        "/api/v1/search",
        json={"query": "test query"}
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_search_suggestions(auth_client: AsyncClient):
    """Test search suggestions endpoint."""
    response = await auth_client.get(
        "/api/v1/search/suggest",
        params={"q": "test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
