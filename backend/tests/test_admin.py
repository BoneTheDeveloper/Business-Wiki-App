"""Tests for admin endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_stats_requires_admin(client: AsyncClient, auth_headers):
    """Test admin stats requires admin role."""
    response = await client.get("/api/v1/admin/stats", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats_success(client: AsyncClient, admin_auth_headers):
    """Test admin stats with admin user."""
    response = await client.get("/api/v1/admin/stats", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "total_users" in data
    assert "total_chunks" in data


@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, admin_auth_headers):
    """Test listing users as admin."""
    response = await client.get("/api/v1/admin/users", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_admin_update_user_role(client: AsyncClient, admin_auth_headers, test_user):
    """Test updating user role as admin."""
    response = await client.patch(
        f"/api/v1/admin/users/{test_user.id}",
        json={"role": "editor"},
        headers=admin_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "editor"


@pytest.mark.asyncio
async def test_admin_cannot_demote_self(client: AsyncClient, admin_auth_headers, admin_user):
    """Test admin cannot demote themselves."""
    response = await client.patch(
        f"/api/v1/admin/users/{admin_user.id}",
        json={"role": "user"},
        headers=admin_auth_headers
    )
    assert response.status_code == 400
