# Phase 02 - Database & Authentication

**Priority:** P0 | **Duration:** 2 days | **Status:** Pending

## Overview

Implement PostgreSQL schema with pgvector, user authentication with JWT, and role-based access control (RBAC).

## Key Insights

- SQLAlchemy 2.0 async patterns
- pgvector extension for vector storage
- JWT access + refresh tokens
- Roles: ADMIN, EDITOR, USER

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
├─────────────────────────────────────────────────────────────┤
│  POST /api/v1/auth/register                                 │
│  POST /api/v1/auth/login        → JWT Access + Refresh      │
│  POST /api/v1/auth/refresh      → New Access Token          │
│  GET  /api/v1/auth/me           → Current User              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL + pgvector                     │
├─────────────────────────────────────────────────────────────┤
│  users (id, email, password_hash, role, is_active)          │
│  documents (id, user_id, filename, status, metadata)        │
│  document_chunks (id, document_id, content, embedding)      │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

### Functional
- User registration with email/password
- Login returns JWT access token (30min) + refresh token (7 days)
- Token refresh endpoint
- RBAC: ADMIN, EDITOR, USER roles
- Protected routes require valid token

### Non-Functional
- Password hashing: bcrypt
- Token validation < 10ms
- Rate limiting on auth endpoints

## Related Files

**Create:**
- `backend/app/models/database.py` - Async engine, session
- `backend/app/models/models.py` - SQLAlchemy models
- `backend/app/models/schemas.py` - Pydantic schemas
- `backend/app/auth/routes.py` - Auth endpoints
- `backend/app/auth/security.py` - JWT, password utils
- `backend/app/dependencies.py` - Auth dependencies

## Implementation Steps

### 1. Database Setup

```python
# backend/app/models/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.run_sync(Base.metadata.create_all)
```

### 2. SQLAlchemy Models

```python
# backend/app/models/models.py
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid
import enum
from datetime import datetime
from app.models.database import Base

class UserRole(str, enum.Enum):
    USER = "user"
    EDITOR = "editor"
    ADMIN = "admin"

class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="user")

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    format = Column(String(20))
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING)
    metadata = Column(JSONB, default=dict)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-small dimensions
    chunk_index = Column(Integer, nullable=False)
    metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")

# Index for vector similarity search
# Note: Created via raw SQL in init_db for IVFFlat
```

### 3. Pydantic Schemas

```python
# backend/app/models/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models.models import UserRole, DocumentStatus

# Auth
class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefresh(BaseModel):
    refresh_token: str

# User
class UserResponse(BaseModel):
    id: UUID
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Document
class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    file_size: Optional[int]
    format: Optional[str]
    status: DocumentStatus
    metadata: dict
    created_at: datetime

    class Config:
        from_attributes = True
```

### 4. Security Module

```python
# backend/app/auth/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
```

### 5. Auth Routes

```python
# backend/app/auth/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import get_db
from app.models.models import User, UserRole
from app.models.schemas import UserRegister, UserLogin, Token, TokenRefresh, UserResponse
from app.auth.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check existing
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.USER
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(403, "Account disabled")

    token_data = {"sub": str(user.id), "role": user.role.value}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data)
    )

@router.post("/refresh", response_model=Token)
async def refresh(data: TokenRefresh):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")

    token_data = {"sub": payload["sub"], "role": payload["role"]}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data)
    )
```

### 6. Dependencies

```python
# backend/app/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import get_db
from app.models.models import User, UserRole
from app.auth.security import decode_token

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(401, "Invalid token")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    return user

def require_role(roles: list[UserRole]):
    async def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return checker
```

## Todo List

- [ ] Create database.py with async engine
- [ ] Create models.py with User, Document, DocumentChunk
- [ ] Create schemas.py with Pydantic models
- [ ] Create security.py with JWT/password utils
- [ ] Create auth/routes.py with register/login/refresh
- [ ] Create dependencies.py with auth middleware
- [ ] Update main.py to include auth routes
- [ ] Add startup event to init pgvector extension
- [ ] Create vector index SQL migration
- [ ] Test: Register user returns 201
- [ ] Test: Login returns valid JWT
- [ ] Test: Protected route rejects invalid token
- [ ] Test: Admin route rejects non-admin user

## Success Criteria

1. User can register with email/password
2. Login returns access + refresh tokens
3. Protected routes require valid Authorization header
4. RBAC blocks unauthorized role access
5. pgvector extension enabled, vector index created

## Next Steps

- Phase 03: Document upload, MinIO integration, file parsing
