"""Tests for auth endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_current_user_info(auth_client: AsyncClient, test_user):
    """Test /auth/me returns current user info."""
    response = await auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_protected_route_without_token(client: AsyncClient):
    """Test protected route rejects request without auth header."""
    response = await client.get("/api/v1/documents")
    assert response.status_code == 403 or response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_malformed_header(client: AsyncClient):
    """Test protected route rejects malformed auth header."""
    response = await client.get(
        "/api/v1/documents",
        headers={"Authorization": "NotBearer sometoken"}
    )
    assert response.status_code == 403 or response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_returns_all_fields(auth_client: AsyncClient, test_user):
    """Test /auth/me response has all expected user fields."""
    response = await auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "email" in data
    assert "role" in data
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_admin_can_access_admin_routes(admin_client: AsyncClient):
    """Test admin user can access admin-only routes."""
    response = await admin_client.get("/api/v1/admin/stats")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_regular_user_cannot_access_admin(auth_client: AsyncClient):
    """Test regular user is forbidden from admin routes."""
    response = await auth_client.get("/api/v1/admin/stats")
    assert response.status_code == 403
