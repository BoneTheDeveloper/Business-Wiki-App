# Phase 08 - Testing & Polish

**Priority:** P1 | **Duration:** 2 days | **Status:** Pending

## Overview

Comprehensive testing, error handling, documentation, and final polish before MVP release.

## Key Insights

- Backend: pytest with async support
- Frontend: Vitest + Vue Test Utils
- E2E: Playwright (optional, time-permitting)
- API docs via FastAPI Swagger
- README with setup instructions

## Testing Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Pyramid                              │
├─────────────────────────────────────────────────────────────┤
│       E2E Tests (Playwright - optional)                     │
│           ↑                                                  │
│     Integration Tests (API + DB)                            │
│           ↑                                                  │
│       Unit Tests (Services, Utils)                          │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

### Functional
- Backend unit tests > 80% coverage
- Frontend component tests for key views
- API integration tests
- Error handling with user-friendly messages
- README with setup instructions

### Non-Functional
- All tests pass in CI
- Test suite runs < 5 minutes
- Clear error messages

## Related Files

**Create:**
- `backend/tests/conftest.py` - Fixtures
- `backend/tests/test_auth.py`
- `backend/tests/test_documents.py`
- `backend/tests/test_search.py`
- `backend/tests/test_chat.py`
- `frontend/src/__tests__/`
- `README.md`

## Implementation Steps

### 1. Backend Test Setup

```python
# backend/tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient
from app.main import app
from app.models.database import Base, get_db
from app.models.models import User, UserRole
from app.auth.security import hash_password

TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/wiki_test"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture
async def test_user(db_session):
    user = User(
        email="test@example.com",
        password_hash=hash_password("password123"),
        role=UserRole.USER,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def auth_headers(client, test_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### 2. Auth Tests

```python
# backend/tests/test_auth.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "user"

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user):
    response = await client.post("/api/v1/auth/register", json={
        "email": test_user.email,
        "password": "password123"
    })
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_protected_route_without_token(client: AsyncClient):
    response = await client.get("/api/v1/documents")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_protected_route_with_token(client: AsyncClient, auth_headers):
    response = await client.get("/api/v1/documents", headers=auth_headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user):
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
    assert "access_token" in response.json()
```

### 3. Document Tests

```python
# backend/tests/test_documents.py
import pytest
from httpx import AsyncClient
import io

@pytest.mark.asyncio
async def test_upload_pdf(client: AsyncClient, auth_headers):
    file_content = b"%PDF-1.4\ntest pdf content"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}

    response = await client.post(
        "/api/v1/documents/upload",
        files=files,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["format"] == "pdf"
    assert data["status"] in ["pending", "processing"]

@pytest.mark.asyncio
async def test_upload_unsupported_format(client: AsyncClient, auth_headers):
    files = {"file": ("test.txt", io.BytesIO(b"text content"), "text/plain")}
    response = await client.post(
        "/api/v1/documents/upload",
        files=files,
        headers=auth_headers
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, auth_headers):
    response = await client.get("/api/v1/documents", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, auth_headers):
    # Upload first
    file_content = b"%PDF-1.4\ntest"
    files = {"file": ("delete_test.pdf", io.BytesIO(file_content), "application/pdf")}
    upload_response = await client.post(
        "/api/v1/documents/upload",
        files=files,
        headers=auth_headers
    )
    doc_id = upload_response.json()["id"]

    # Delete
    response = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert response.status_code == 200

    # Verify deleted
    get_response = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert get_response.status_code == 404
```

### 4. Search Tests

```python
# backend/tests/test_search.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_search_without_query(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/search",
        json={"query": ""},
        headers=auth_headers
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_search_too_short(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/search",
        json={"query": "ab"},
        headers=auth_headers
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_search_returns_results(client: AsyncClient, auth_headers, document_with_chunks):
    response = await client.post(
        "/api/v1/search",
        json={"query": "test query", "top_k": 5},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
```

### 5. Chat Tests

```python
# backend/tests/test_chat.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_chat_without_documents(client: AsyncClient, auth_headers):
    """Chat should return helpful message when no documents"""
    response = await client.post(
        "/api/v1/chat",
        json={"query": "What is the policy?"},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data

@pytest.mark.asyncio
async def test_chat_with_short_query(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/chat",
        json={"query": "hi"},
        headers=auth_headers
    )
    assert response.status_code == 400
```

### 6. Frontend Tests (Vitest)

```typescript
// frontend/src/__tests__/authStore.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/authStore'

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('starts unauthenticated', () => {
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
  })

  it('logout clears state', () => {
    const store = useAuthStore()
    store.user = { id: '1', email: 'test@example.com', role: 'user', is_active: true }
    store.accessToken = 'token'

    store.logout()

    expect(store.user).toBeNull()
    expect(store.accessToken).toBeNull()
  })
})
```

### 7. README

```markdown
# RAG Business Document Wiki

A RAG-powered document wiki application with Vue.js frontend and FastAPI backend.

## Features

- 📄 Document upload (PDF, DOCX, XLSX)
- 🔍 Semantic search across documents
- 💬 Chat with your documents using RAG
- 👤 User authentication with JWT
- 🛡️ Role-based access control
- ⚡ Real-time processing status

## Tech Stack

- **Frontend:** Vue.js 3, TypeScript, PrimeVue, Tailwind CSS
- **Backend:** FastAPI, SQLAlchemy, Pydantic
- **Database:** PostgreSQL + pgvector
- **Cache/Queue:** Redis, Celery
- **Storage:** MinIO
- **AI:** OpenAI (embeddings + chat)

## Prerequisites

- Docker & Docker Compose
- OpenAI API key

## Quick Start

1. Clone the repository:
```bash
git clone <repo-url>
cd bussiness_wiki_app
```

2. Create `.env` file:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. Start services:
```bash
docker-compose up -d
```

4. Access the application:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs
- MinIO Console: http://localhost:9001

## Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Run Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run test
```

## Project Structure

```
├── frontend/          # Vue.js 3 frontend
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/
│   │   └── api/
│   └── package.json
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── models/
│   │   └── services/
│   └── requirements.txt
└── docker-compose.yml
```

## API Endpoints

### Auth
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token

### Documents
- `GET /api/v1/documents` - List documents
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents/{id}` - Get document
- `DELETE /api/v1/documents/{id}` - Delete document

### Search & Chat
- `POST /api/v1/search` - Semantic search
- `POST /api/v1/chat` - Chat with documents

### Admin
- `GET /api/v1/admin/users` - List users
- `PATCH /api/v1/admin/users/{id}` - Update user
- `GET /api/v1/admin/stats` - System stats

## License

MIT
```

## Todo List

- [ ] Create tests/conftest.py with fixtures
- [ ] Create test_auth.py
- [ ] Create test_documents.py
- [ ] Create test_search.py
- [ ] Create test_chat.py
- [ ] Create frontend component tests
- [ ] Add error handling middleware
- [ ] Create README.md
- [ ] Run all tests and ensure pass
- [ ] Check test coverage > 80%

## Success Criteria

1. All backend tests pass
2. Auth, documents, search, chat covered
3. Frontend tests for key stores
4. README with clear setup instructions
5. API docs accessible via Swagger
6. Error messages user-friendly

## MVP Complete!

After this phase, the MVP is ready for deployment.

### Deployment Checklist
- [ ] Set production JWT secret
- [ ] Configure production database
- [ ] Set up SSL/TLS
- [ ] Configure backups
- [ ] Set up monitoring
- [ ] Create admin user
