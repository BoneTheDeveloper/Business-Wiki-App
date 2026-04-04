"""Tests for admin endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_stats_requires_admin(auth_client: AsyncClient):
    """Test admin stats requires admin role — regular user gets 403."""
    response = await auth_client.get("/api/v1/admin/stats")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats_success(admin_client: AsyncClient):
    """Test admin stats with admin user."""
    response = await admin_client.get("/api/v1/admin/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "total_users" in data


@pytest.mark.asyncio
async def test_admin_list_users(admin_client: AsyncClient):
    """Test listing users as admin."""
    response = await admin_client.get("/api/v1/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_admin_update_user_role(admin_client: AsyncClient, test_user):
    """Test updating user role as admin."""
    response = await admin_client.patch(
        f"/api/v1/admin/users/{test_user.id}",
        json={"role": "editor"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "editor"


@pytest.mark.asyncio
async def test_admin_cannot_demote_self(admin_client: AsyncClient, admin_user):
    """Test admin cannot demote themselves."""
    response = await admin_client.patch(
        f"/api/v1/admin/users/{admin_user.id}",
        json={"role": "user"},
    )
    assert response.status_code == 400
