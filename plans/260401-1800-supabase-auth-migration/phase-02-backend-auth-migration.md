---
title: "Phase 2: Backend Auth Migration"
phase: 2
status: pending
effort: 6h
depends_on: [phase-01]
---

# Phase 2: Backend Auth Migration

## Context
- Plan: [plan.md](plan.md)
- Phase 1: [phase-01-local-dev-infrastructure.md](phase-01-local-dev-infrastructure.md)
- Supabase migrations must be applied before starting this phase

## Overview
Replace all custom JWT creation/verification, password hashing, and OAuth handling with Supabase JWT validation via JWKS. Backend becomes a passive token validator -- it never creates or issues tokens.

## Requirements

### Functional
- `get_current_user` dependency validates Supabase JWT (RS256 via JWKS)
- `/auth/me` endpoint returns user from DB based on JWT `sub` claim
- Role-based access control (`require_role`, `require_admin`, etc.) reads role from DB
- On first request from a new Supabase user, backend auto-creates `public.users` row (belt-and-suspenders alongside DB trigger)

### Non-Functional
- JWKS keys cached with 1-hour TTL to avoid per-request network call
- Token validation < 5ms (after JWKS cache warmup)
- No password hashing, no JWT signing, no OAuth flow in backend

## Architecture

```
Request flow:
1. Client sends: Authorization: Bearer <supabase_access_token>
2. Backend extracts token from header
3. Backend validates token:
   a. Fetch signing key from JWKS cache (or Supabase /.well-known/jwks.json)
   b. Verify RS256 signature
   c. Verify audience = "authenticated"
   d. Verify issuer = "{SUPABASE_URL}/auth/v1"
   e. Check expiry
4. Extract `sub` (user_id) from verified payload
5. Look up user in public.users by id
6. If user not found: auto-create from JWT claims (first-login fallback)
7. Check is_active, role, etc.
```

## Related Code Files

### Modify
- `backend/app/auth/security.py` -- Replace with JWKS-based validation
- `backend/app/auth/routes.py` -- Remove login/register/oauth endpoints, keep /auth/me
- `backend/app/dependencies.py` -- Use Supabase JWT validation
- `backend/app/config.py` -- Remove JWT_SECRET_KEY/ALGORITHM/EXPIRE_MINUTES, GOOGLE_*, APP_URL, OAUTH_AUTO_REGISTER
- `backend/app/models/user.py` -- Remove password_hash, oauth_provider, oauth_id columns
- `backend/app/models/__init__.py` -- Remove SocialAccount if needed
- `backend/app/schemas/auth.py` -- Remove UserLogin, UserRegister, Token, TokenRefresh; add SupabaseUserPayload

### Delete
- `backend/app/auth/oauth.py` -- Supabase handles OAuth entirely
- `backend/app/services/oauth_service.py` -- No longer needed

### Keep (no changes)
- `backend/app/models/social_account.py` -- Keep model for now, just stop writing to it
- `backend/app/schemas/user.py` -- UserResponse stays the same (minus oauth_provider field)

## Implementation Steps

### Step 1: Create `backend/app/auth/supabase.py`

New file for Supabase JWT verification via JWKS.

```python
"""Supabase JWT verification using JWKS (RS256)."""
import time
from typing import Optional
from jose import jwt, JWTError, JWKSError
import httpx
from app.config import settings


class JWKSCache:
    """Cache JWKS keys with TTL to avoid per-request network calls."""

    def __init__(self, ttl_seconds: int = 3600):
        self._jwks: Optional[dict] = None
        self._fetched_at: float = 0
        self._ttl = ttl_seconds

    async def get_jwks(self) -> dict:
        """Fetch JWKS from Supabase, using cache if fresh."""
        now = time.time()
        if self._jwks and (now - self._fetched_at) < self._ttl:
            return self._jwks

        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            self._jwks = resp.json()
            self._fetched_at = now
            return self._jwks


jwks_cache = JWKSCache()


async def verify_supabase_token(token: str) -> dict:
    """
    Verify a Supabase-issued JWT access token.

    Returns the decoded payload with claims:
    - sub: user UUID
    - email: user email
    - app_role: application role (from custom hook)
    - role: always "authenticated" (Postgres role, not app role)

    Raises HTTPException(401) on invalid/expired tokens.
    """
    from fastapi import HTTPException, status

    try:
        jwks = await jwks_cache.get_jwks()
        issuer = f"{settings.SUPABASE_URL}/auth/v1"

        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience="authenticated",
            issuer=issuer,
        )
        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to verify token: {str(e)}",
        )
```

### Step 2: Replace `backend/app/auth/security.py`

Replace entire file. Remove `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`, `decode_token`. Re-export `verify_supabase_token` for backward compat.

```python
"""Security utilities -- Supabase JWT validation only."""
# All auth operations (signup, login, password reset, OAuth) handled by Supabase.
# This module re-exports the JWT verification function for use in dependencies.

from app.auth.supabase import verify_supabase_token, jwks_cache

__all__ = ["verify_supabase_token", "jwks_cache"]
```

### Step 3: Rewrite `backend/app/auth/routes.py`

Remove all endpoints except `/auth/me`. No login, register, refresh, or OAuth routes.

```python
"""Authentication API routes -- Supabase Auth proxy."""
from fastapi import APIRouter, Depends
from app.models.database import get_db
from app.schemas.user import UserResponse
from app.dependencies import get_current_user
from app.models.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info from Supabase JWT."""
    return current_user
```

### Step 4: Rewrite `backend/app/dependencies.py`

Update `get_current_user` to validate Supabase JWT and auto-create user on first login.

```python
"""FastAPI dependencies for authentication and authorization."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.models.database import get_db
from app.models.models import User, UserRole
from app.auth.supabase import verify_supabase_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate Supabase JWT and return the app user."""
    payload = await verify_supabase_token(credentials.credentials)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing sub claim",
        )

    # Look up user in public.users
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    # Auto-create user on first login (belt-and-suspenders with DB trigger)
    if not user:
        email = payload.get("email", "")
        metadata = payload.get("app_metadata", {})
        user_metadata = payload.get("user_metadata", {})

        user = User(
            id=user_id,
            email=email,
            email_verified=payload.get("email_confirmed", False),
            name=user_metadata.get("name") or email.split("@")[0],
            avatar_url=user_metadata.get("avatar_url"),
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )

    return user


def require_role(roles: List[UserRole]):
    """Dependency factory to require specific app roles."""
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user
    return role_checker


# Common role dependencies (unchanged)
require_admin = require_role([UserRole.ADMIN])
require_editor = require_role([UserRole.ADMIN, UserRole.EDITOR])
require_user = require_role([UserRole.ADMIN, UserRole.EDITOR, UserRole.USER])
```

### Step 5: Update `backend/app/config.py`

Remove JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, APP_URL, OAUTH_AUTO_REGISTER.

```python
"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    SUPABASE_URL: str = "http://127.0.0.1:54321"
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Database (default: local Supabase stack)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "documents"
    MINIO_SECURE: bool = False

    # OpenAI
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
```

### Step 6: Update `backend/app/models/user.py`

Remove `password_hash`, `oauth_provider`, `oauth_id` columns. Remove the `social_accounts` relationship (keep model file but decouple).

```python
"""User model -- synced from Supabase Auth via DB trigger."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.database import Base
from app.models.enums import UserRole


class User(Base):
    """User model. Row created automatically when Supabase Auth user signs up."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    # No password_hash -- Supabase Auth manages passwords
    # No oauth_provider/oauth_id -- Supabase Auth manages identities
    email_verified = Column(Boolean, nullable=True)
    name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(20), default=UserRole.USER.value, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="user")
    owned_organizations = relationship("Organization", foreign_keys="Organization.owner_id", back_populates="owner")
    organization_memberships = relationship(
        "OrganizationMember", foreign_keys="OrganizationMember.user_id",
        back_populates="user", cascade="all, delete-orphan",
    )
    group_memberships = relationship(
        "GroupMember", foreign_keys="GroupMember.user_id",
        back_populates="user", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_users_email", "email"),
    )
```

### Step 7: Update `backend/app/models/__init__.py`

Keep SocialAccount import but it won't be actively used. No import changes needed beyond what's already there.

### Step 8: Update `backend/app/schemas/auth.py`

Replace with minimal schema. Login/register/token schemas no longer needed.

```python
"""Auth-related Pydantic schemas -- Supabase JWT payload."""
from pydantic import BaseModel
from typing import Optional


class SupabaseUserPayload(BaseModel):
    """Decoded Supabase JWT payload (useful for internal typing)."""
    sub: str  # user UUID
    email: str
    role: str  # always "authenticated" (Postgres role)
    app_role: Optional[str] = None  # injected by custom hook
    email_confirmed: Optional[bool] = None
```

### Step 9: Update `backend/app/schemas/user.py`

Remove `oauth_provider` from UserResponse.

```python
"""User-related Pydantic schemas."""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.enums import UserRole


class UserResponse(BaseModel):
    """User response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    is_active: bool
    email_verified: Optional[bool] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime


class UserUpdate(BaseModel):
    """User update request (admin)."""
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
```

### Step 10: Delete `backend/app/auth/oauth.py`

```bash
rm backend/app/auth/oauth.py
```

### Step 11: Delete `backend/app/services/oauth_service.py`

```bash
rm backend/app/services/oauth_service.py
```

### Step 12: Remove unused dependencies from `backend/pyproject.toml`

Remove `passlib`, `authlib`, `itsdangerous` from dependencies. Keep `python-jose` (still needed for JWT decoding) and `bcrypt` can be removed if nothing else uses it. Keep `httpx` (needed for JWKS fetching).

Verify: `python-jose[cryptography]` is needed for RS256. Ensure it's in deps.

### Step 13: Fix any route files importing deleted modules

Files that import from deleted modules:
- `backend/app/api/v1/routes/admin.py` -- uses `get_current_user`, `require_admin` (unchanged interface)
- `backend/app/api/v1/routes/documents.py` -- uses `get_current_user` (unchanged)
- `backend/app/api/v1/routes/groups.py` -- uses `get_current_user` (unchanged)
- `backend/app/api/v1/routes/invitations.py` -- uses `get_current_user` (unchanged)
- `backend/app/api/v1/routes/organizations.py` -- uses `get_current_user` (unchanged)
- `backend/app/api/v1/routes/search.py` -- uses `get_current_user` (unchanged)
- `backend/app/api/v1/routes/chat.py` -- uses `get_current_user` (unchanged)

All these import `from app.dependencies import get_current_user` which keeps the same interface. **No changes needed** in these route files.

## Todo Checklist

- [ ] Create `backend/app/auth/supabase.py` with JWKSCache and verify_supabase_token
- [ ] Replace `backend/app/auth/security.py` with re-exports
- [ ] Rewrite `backend/app/auth/routes.py` (remove login/register/oauth/refresh, keep /auth/me)
- [ ] Rewrite `backend/app/dependencies.py` (Supabase JWT validation + auto-create)
- [ ] Update `backend/app/config.py` (remove JWT/OAuth settings)
- [ ] Update `backend/app/models/user.py` (remove password_hash, oauth columns)
- [ ] Update `backend/app/schemas/auth.py` (replace with SupabaseUserPayload)
- [ ] Update `backend/app/schemas/user.py` (remove oauth_provider)
- [ ] Delete `backend/app/auth/oauth.py`
- [ ] Delete `backend/app/services/oauth_service.py`
- [ ] Remove unused deps from pyproject.toml (passlib, authlib, itsdangerous)
- [ ] Add `httpx` to pyproject.toml if not present
- [ ] Run `uv sync` or `poetry install` to update lockfile
- [ ] Run compile check: `uv run python -c "from app.main import app"`
- [ ] Verify all route files still work with new dependencies

## Success Criteria
- Backend starts without import errors
- `GET /auth/me` with valid Supabase JWT returns user data
- `GET /auth/me` with invalid/expired token returns 401
- `require_admin`, `require_editor`, `require_user` work correctly
- First login from new Supabase user auto-creates `public.users` row
- No references to `hash_password`, `create_access_token`, `oauth.google` anywhere in backend

## Risk Assessment
- **JWKS fetch failure:** If Supabase is unreachable, all auth fails. Mitigated by JWKS cache with 1h TTL.
- **RS256 key mismatch:** Supabase rotates signing keys. JWKS endpoint always has current keys. Cache TTL of 1h handles rotation gracefully.
- **`email_confirmed` claim:** Supabase JWT may not include `email_confirmed` directly. Fallback: check if `email_confirmed_at` is present in payload or use DB `email_verified` column.
- **Auto-create race condition:** DB trigger and auto-create in `get_current_user` could race. `INSERT ... ON CONFLICT DO NOTHING` or try/except on duplicate key handles this.

## Security Considerations
- JWT audience must be `"authenticated"` -- prevents token misuse across Supabase projects
- JWT issuer must match `SUPABASE_URL` -- prevents token injection from other Supabase instances
- JWKS fetched over HTTPS in production (enforced by Supabase URL)
- No password handling in backend -- eliminates password leak surface area
- Auto-create only sets `role=USER` -- no privilege escalation on first login

## Next Steps
- Phase 3 (frontend) can proceed in parallel once backend compiles
- Phase 4 (testing) requires both backend and frontend to be migrated
