"""Pytest configuration and fixtures for backend tests."""
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.database import Base, get_db
from app.models.models import User, UserRole

# Use SQLite for testing (no external DB needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest.fixture
async def client(db_session):
    """Create test HTTP client with DB override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user (simulates Supabase-auth-synced user)."""
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
async def admin_user(db_session: AsyncSession):
    """Create an admin test user (simulates Supabase-auth-synced user)."""
    user = User(
        email="admin@example.com",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_headers(client: AsyncClient, test_user: User):
    """Get auth headers with mocked Supabase JWT for test user."""
    # In Supabase auth world, tests need to mock verify_supabase_token
    # For now, return a placeholder header -- individual tests should mock
    # the get_current_user dependency directly.
    return {"Authorization": f"Bearer test-token-{test_user.id}"}


@pytest.fixture
async def admin_auth_headers(client: AsyncClient, admin_user: User):
    """Get auth headers with mocked Supabase JWT for admin user."""
    return {"Authorization": f"Bearer test-token-{admin_user.id}"}
