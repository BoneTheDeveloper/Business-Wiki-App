"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "password123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "user"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user):
    """Test registration with existing email fails."""
    response = await client.post("/api/v1/auth/register", json={
        "email": test_user.email,
        "password": "password123"
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """Test successful login."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Test login with wrong password."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with nonexistent user."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "password123"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, auth_headers):
    """Test getting current user info."""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_protected_route_without_token(client: AsyncClient):
    """Test protected route rejects missing token."""
    response = await client.get("/api/v1/documents")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_invalid_token(client: AsyncClient):
    """Test protected route rejects invalid token."""
    response = await client.get(
        "/api/v1/documents",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user):
    """Test token refresh."""
    # Login first
    login_response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    refresh_token = login_response.json()["refresh_token"]

    # Refresh
    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
