"""Tests for search endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_search_empty_query(client: AsyncClient, auth_headers):
    """Test search with empty query."""
    response = await client.post(
        "/api/v1/search",
        json={"query": ""},
        headers=auth_headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_search_too_short(client: AsyncClient, auth_headers):
    """Test search with too short query."""
    response = await client.post(
        "/api/v1/search",
        json={"query": "ab"},
        headers=auth_headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_search_no_documents(client: AsyncClient, auth_headers):
    """Test search when no documents exist."""
    response = await client.post(
        "/api/v1/search",
        json={"query": "test query"},
        headers=auth_headers
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
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_suggestions(client: AsyncClient, auth_headers):
    """Test search suggestions endpoint."""
    response = await client.get(
        "/api/v1/search/suggest",
        params={"q": "test"},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
