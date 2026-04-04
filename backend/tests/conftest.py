"""Pytest configuration and fixtures for backend tests.

Two DB modes:
  1. SQLite in-memory (default) — fast, no Docker. pgvector features skipped.
  2. Testcontainers PG (CI / TEST_USE_DOCKER=true) — real PG + pgvector.

Auth is always mocked via FastAPI dependency override — no real Supabase calls.
"""
import os
import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.database import Base, get_db
from app.models.models import User, UserRole
from app.dependencies import get_current_user

USE_DOCKER = os.environ.get("TEST_USE_DOCKER", "false").lower() == "true"


# ── Pytest Hooks ──────────────────────────────────────────────────

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "pgvector: requires real PostgreSQL + pgvector (Docker)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip pgvector tests when Docker not available."""
    if USE_DOCKER:
        return
    skip = pytest.mark.skip(
        reason="Requires Docker + pgvector (set TEST_USE_DOCKER=true)"
    )
    for item in items:
        if "pgvector" in item.keywords:
            item.add_marker(skip)


# ── Session-scoped Engine ─────────────────────────────────────────

@pytest.fixture(scope="session")
def _engine_url() -> str:
    """Database URL for current mode."""
    if USE_DOCKER:
        from testcontainers.postgres import PostgresContainer
        pg = PostgresContainer("pgvector/pgvector:pg16")
        pg.start()
        url = pg.get_connection_url().replace("psycopg2", "asyncpg")
        # Store container for cleanup
        os.environ["_TC_PG_CONTAINER"] = pg.get_container_host_ip()
        return url
    return "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
async def db_engine(_engine_url):
    """Create async engine — SQLite by default, Testcontainers PG if Docker."""
    engine = create_async_engine(_engine_url, echo=False)

    async with engine.begin() as conn:
        if USE_DOCKER:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


# ── Per-test DB Session (with cleanup) ────────────────────────────

@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create isolated DB session per test.

    Drops and recreates all tables between tests for clean state.
    """
    # Drop and recreate for clean state (safe for in-memory SQLite)
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


# ── HTTP Client ───────────────────────────────────────────────────

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with DB session override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Test Users ────────────────────────────────────────────────────

@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a regular test user."""
    user = User(
        email="test@example.com",
        role=UserRole.USER,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        email="admin@example.com",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ── Auth Dependency Overrides ─────────────────────────────────────

@pytest.fixture
async def auth_client(client: AsyncClient, test_user: User) -> AsyncClient:
    """HTTP client with get_current_user returning test_user."""
    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def admin_client(client: AsyncClient, admin_user: User) -> AsyncClient:
    """HTTP client with get_current_user returning admin_user."""
    async def mock_get_current_user():
        return admin_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)
