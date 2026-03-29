# Code Standards - RAG Business Document Wiki

**Last Updated:** 2026-03-27
**Language:** Python 3.11+, TypeScript 5.3+

## General Principles

### Core Philosophy
- **YAGNI**: Don't build what you don't need yet
- **KISS**: Keep implementations simple and straightforward
- **DRY**: Don't repeat yourself - extract common logic

### File Naming Conventions

**Backend (Python)**
- Modules: `snake_case.py` (e.g., `rag_service.py`, `user_service.py`)
- Classes: `PascalCase` (e.g., `UserService`, `DocumentProcessor`)
- Functions: `snake_case` (e.g., `get_user_by_email()`, `process_document()`)
- Private methods: `snake_case` with leading underscore (e.g., `_validate_email()`)

**Frontend (TypeScript/Vue)**
- Components: `kebab-case.vue` (e.g., `document-card.vue`, `chat-interface.vue`)
- Files: `kebab-case.ts` (e.g., `api-client.ts`, `use-auth.ts`)
- Functions: `camelCase` (e.g., `getUserById()`, `processDocument()`)
- Private methods: `camelCase` with leading underscore (e.g., `_validateForm()`)

### File Size Management
- Keep individual files under **200 lines** for optimal context management
- Split large files into smaller, focused components/modules
- Extract utility functions into separate modules
- Create dedicated service classes for business logic

## Python Code Standards

### Structure

**Directory Layout**
```
backend/app/
├── api/
│   └── v1/
│       └── routes/
│           ├── admin.py         # Admin endpoints
│           ├── documents.py     # Document endpoints
│           └── search.py        # Search endpoints
├── auth/
│   ├── routes.py               # Auth endpoints
│   └── security.py             # JWT, password hashing
├── models/
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   └── database.py             # DB initialization
├── services/
│   ├── celery_tasks.py         # Async tasks
│   ├── llm_service.py          # OpenAI integration
│   └── rag_service.py          # RAG pipeline
└── utils/
    └── websocket.py            # WebSocket utilities
```

### Import Organization
```python
# Standard library imports first
import os
import sys
from datetime import datetime
from typing import Optional, List

# Third-party imports
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

# Local imports
from app.models import User, Document
from app.schemas import UserCreate, UserResponse
from app.services import rag_service

# Constants
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
```

### Type Hints (Required)
```python
from typing import Optional, List, Dict
from datetime import datetime

def process_document(
    document_id: str,
    user_id: str,
    status: str = "pending"
) -> Document:
    """Process a document asynchronously.

    Args:
        document_id: UUID of the document
        user_id: UUID of the user
        status: Processing status

    Returns:
        Processed document object
    """
    # Implementation
    pass

async def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email.

    Args:
        email: User email address

    Returns:
        User object or None if not found
    """
    # Implementation
    pass
```

### Error Handling
```python
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

def get_document(document_id: str) -> Document:
    """Get document by ID with error handling."""
    try:
        document = db.query(Document).filter(
            Document.id == document_id
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        return document

    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
```

### Async/Await Usage
```python
from fastapi import BackgroundTasks

async def upload_document(
    file: UploadFile,
    user_id: str,
    background_tasks: BackgroundTasks
) -> dict:
    """Upload and process document asynchronously."""
    # Validate file
    if not allowed_formats(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format"
        )

    # Upload to MinIO
    file_path = await minio_service.upload_file(file)

    # Create DB record
    document = Document(
        user_id=user_id,
        filename=file.filename,
        file_path=file_path
    )
    db.add(document)
    db.commit()

    # Dispatch Celery task
    background_tasks.add_task(
        celery_tasks.process_document,
        document_id=document.id
    )

    return {"id": document.id, "status": "pending"}

# Celery task
@celery_app.task
def process_document(document_id: str) -> None:
    """Process document asynchronously."""
    try:
        # Implementation
        pass
    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise
```

### Database Operations
```python
from sqlalchemy.orm import Session

def get_user_with_documents(
    db: Session,
    user_id: str
) -> User:
    """Get user with documents in one query."""
    return db.query(User).filter(
        User.id == user_id
    ).options(
        joinedload(User.documents)
    ).first()
```

### Configuration Management
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    database_url: str
    redis_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    openai_api_key: str
    minio_endpoint: str

    class Config:
        env_file = ".env"

settings = Settings()
```

## TypeScript Code Standards

### File Structure
```
frontend/src/
├── api/
│   └── client.ts                 # Axios client
├── components/
│   ├── DocumentCard.vue         # Reusable component
│   └── ChatMessage.vue
├── composables/
│   └── use-web-socket.ts        # Reusable composable
├── router/
│   └── index.ts                 # Route configuration
├── stores/
│   ├── auth-store.ts            # Auth state
│   └── document-store.ts        # Document state
├── views/
│   ├── Dashboard.vue
│   ├── Chat.vue
│   └── Admin.vue
└── main.ts                      # App entry
```

### Component Structure
```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth-store'
import { fetchDocuments } from '@/api/client'

// Props
interface Props {
  documentId?: string
}

const props = withDefaults(defineProps<Props>(), {
  documentId: ''
})

// Emits
interface Emits {
  (e: 'update', value: Document): void
  (e: 'delete', value: string): void
}

const emit = defineEmits<Emits>()

// State
const document = ref<Document | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// Computed
const formattedStatus = computed(() => {
  if (!document.value) return 'Unknown'
  return document.value.status.toUpperCase()
})

// Methods
const loadDocument = async () => {
  loading.value = true
  try {
    document.value = await fetchDocumentById(props.documentId)
  } catch (err) {
    error.value = 'Failed to load document'
    console.error(err)
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadDocument()
})
</script>

<template>
  <div class="document-card">
    <div v-if="loading" class="loading">
      <Spinner />
    </div>

    <div v-else-if="error" class="error">
      {{ error }}
    </div>

    <div v-else-if="document" class="content">
      <h3>{{ document.filename }}</h3>
      <p>Status: {{ formattedStatus }}</p>
      <button @click="emit('delete', document.id)">
        Delete
      </button>
    </div>
  </div>
</template>

<style scoped>
.document-card {
  padding: 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.loading, .error {
  padding: 1rem;
}
</style>
```

### Store Structure (Pinia)
```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login, register, logout } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const isAuthenticated = computed(() => !!token.value)

  // Actions
  async function login(email: string, password: string) {
    const response = await login({ email, password })
    user.value = response.user
    token.value = response.token
    localStorage.setItem('auth_token', response.token)
  }

  async function register(data: RegisterRequest) {
    const response = await register(data)
    user.value = response.user
    token.value = response.token
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('auth_token')
  }

  return {
    user,
    token,
    isAuthenticated,
    login,
    register,
    logout
  }
})
```

### API Client Structure
```typescript
import axios, { AxiosInstance, AxiosError } from 'axios'
import { useAuthStore } from '@/stores/auth-store'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const client: AxiosInstance = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
client.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      const authStore = useAuthStore()
      authStore.logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
```

## API Design Standards

### RESTful Conventions
- **GET**: Retrieve resources (no body)
- **POST**: Create resources
- **PUT**: Update entire resource
- **PATCH**: Update partial resource
- **DELETE**: Delete resource

### Request/Response Format
```python
# Request (JSON)
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}

# Response (JSON)
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid-here",
    "email": "user@example.com",
    "role": "user"
  }
}
```

### Error Responses
```python
# 400 Bad Request
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "invalid email address",
      "type": "value_error.email"
    }
  ]
}

# 401 Unauthorized
{
  "detail": "Not authenticated"
}

# 403 Forbidden
{
  "detail": "Not enough permissions"
}

# 404 Not Found
{
  "detail": "Document not found"
}

# 500 Internal Server Error
{
  "detail": "Internal server error"
}
```

## Testing Standards

### Python Tests
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    """Test successful login."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_upload_document(async_client: AsyncClient, auth_token: str):
    """Test document upload."""
    files = {"file": ("test.pdf", b"fake content", "application/pdf")}
    headers = {"Authorization": f"Bearer {auth_token}"}

    response = await async_client.post(
        "/api/v1/documents/upload",
        files=files,
        headers=headers
    )

    assert response.status_code == 200
    assert "id" in response.json()
```

### TypeScript Tests
```typescript
import { describe, it, expect, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth-store'
import { login } from '@/api/client'

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore().$reset()
  })

  it('should login successfully', async () => {
    const authStore = useAuthStore()
    const mockUser = { id: '1', email: 'test@example.com', token: 'abc' }

    vi.mocked(login).mockResolvedValueOnce(mockUser)

    await authStore.login('test@example.com', 'password')

    expect(authStore.user).toEqual(mockUser)
    expect(authStore.isAuthenticated).toBe(true)
  })
})
```

## Security Standards

### Authentication
- **JWT Tokens**: Short-lived (30 minutes), refresh mechanism
- **Password Hashing**: Bcrypt with salt rounds ≥ 12
- **HTTPS**: Required in production

### Authorization
- **Role-Based Access Control (RBAC)**: Enforce at API level
- **Endpoint Protection**: Admin endpoints check user role
- **Resource Ownership**: Users can only access their own documents

### Data Protection
- **Sensitive Data**: Never log passwords, API keys
- **CORS**: Configure allowed origins only
- **Input Validation**: Validate all user inputs
- **SQL Injection**: Use SQLAlchemy ORM (parameterized queries)

## Documentation Standards

### Docstrings
```python
def process_document(document_id: str, user_id: str) -> dict:
    """Process a document asynchronously.

    This function handles document parsing, text extraction,
    chunking, and embedding generation.

    Args:
        document_id: UUID of the document to process
        user_id: UUID of the user requesting processing

    Returns:
        Dictionary with processing status and metadata

    Raises:
        ValueError: If document_id is invalid
        ProcessingError: If parsing fails

    Example:
        >>> result = process_document("123e4567-e89b-12d3", "abc")
        >>> print(result["status"])  # 'completed'
    """
    pass
```

### Code Comments
```python
# Constants
DEFAULT_CHUNK_SIZE = 500  # Characters per chunk
DEFAULT_CHUNK_OVERLAP = 50  # Overlap between chunks

# TODO: Implement caching for embeddings
# FIXME: Handle large files (>10MB) better
# NOTE: OpenAI API has rate limits, need to implement backoff

# Hardcoded value - replace with environment variable
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB
```

### Git Commit Messages
```
feat: add document upload functionality
fix: resolve vector search timeout issue
docs: update API documentation
refactor: extract common validation logic
test: add unit tests for auth endpoints
chore: upgrade dependencies to latest versions
```

## Code Review Checklist

### Functional Requirements
- [ ] Code implements required functionality
- [ ] All edge cases handled
- [ ] Error scenarios covered
- [ ] Input validation present

### Code Quality
- [ ] Follows coding standards
- [ ] Appropriate use of types
- [ ] Clear variable names
- [ ] Well-documented with docstrings
- [ ] No code duplication (DRY)

### Testing
- [ ] Unit tests written
- [ ] Tests cover main scenarios
- [ ] Tests include error cases
- [ ] No skipped tests

### Security
- [ ] Authentication checks present
- [ ] Authorization checks present
- [ ] No sensitive data logged
- [ ] Input validation implemented
- [ ] SQL injection protected

### Performance
- [ ] No N+1 query problems
- [ ] Database queries optimized
- [ ] Caching where appropriate
- [ ] No unnecessary computations

### Maintainability
- [ ] Code is readable and self-documenting
- [ ] Functions have single responsibility
- [ ] Complex logic explained
- [ ] Follows existing patterns
