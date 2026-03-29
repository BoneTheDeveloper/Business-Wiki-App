# Phase 5: Security Hardening

**Priority:** P1 | **Status:** Pending | **Effort:** 1h

## Context

- Research: `plans/reports/researcher-260327-1108-google-oauth-implementation.md`
- Depends on: Phase 2, Phase 3
- Auth routes: `backend/app/auth/`

## Overview

Implement security best practices for OAuth: rate limiting, session management, token security, and audit logging.

## Key Insights

1. Rate limiting prevents OAuth endpoint abuse
2. Short-lived OAuth sessions reduce attack window
3. Token rotation prevents replay attacks
4. Audit logging tracks authentication events

## Requirements

### Functional
- Rate limiting on OAuth endpoints
- Session timeout for OAuth flow
- Token rotation on refresh
- Audit logging for auth events

### Non-Functional
- Rate limit: 10 requests/minute per IP
- OAuth session: 10 minute max
- Audit logs retained 30 days

## Architecture

```
Security Layers:
┌─────────────────────────────────────────────────┐
│ 1. Rate Limiting (per IP)                       │
│ 2. State Parameter (CSRF protection)            │
│ 3. PKCE (code interception protection)          │
│ 4. Session Timeout (10 min max)                 │
│ 5. Token Rotation (refresh tokens)              │
│ 6. Audit Logging (auth events)                  │
└─────────────────────────────────────────────────┘
```

## Related Code Files

### Modify
- `backend/app/main.py` - Add rate limiting middleware
- `backend/app/auth/oauth_routes.py` - Add rate limiter
- `backend/app/auth/security.py` - Token rotation

### Create
- `backend/app/middleware/rate_limit.py` - Rate limiting
- `backend/app/services/audit_service.py` - Audit logging

## Implementation Steps

### Step 1: Add Rate Limiting

```python
# backend/app/middleware/rate_limit.py

from fastapi import Request, HTTPException
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimiter:
    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> bool:
        """Check if request is allowed. Returns True if allowed."""
        async with self._lock:
            now = datetime.utcnow()
            minute_ago = now - timedelta(minutes=1)

            # Clean old requests
            self.requests[key] = [
                t for t in self.requests[key] if t > minute_ago
            ]

            if len(self.requests[key]) >= self.requests_per_minute:
                return False

            self.requests[key].append(now)
            return True

    async def middleware(self, request: Request, call_next):
        # Only rate limit OAuth endpoints
        if '/oauth/' in request.url.path:
            client_ip = request.client.host
            if not await self.check(f"oauth:{client_ip}"):
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later."
                )

        return await call_next(request)


# Global rate limiter instance
oauth_rate_limiter = RateLimiter(requests_per_minute=10)
```

### Step 2: Apply Rate Limiting

```python
# backend/app/main.py

from app.middleware.rate_limit import oauth_rate_limiter

# Add rate limiting middleware
app.middleware("http")(oauth_rate_limiter.middleware)
```

### Step 3: Token Rotation

```python
# backend/app/auth/security.py

from datetime import datetime, timedelta
from typing import Optional
import secrets

# Store for refresh token tracking (use Redis in production)
_refresh_token_store = {}

def create_refresh_token(data: dict, old_token: Optional[str] = None) -> str:
    """Create a new refresh token with rotation."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": secrets.token_urlsafe(16)  # Unique token ID
    })

    new_token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # Invalidate old token if rotating
    if old_token:
        _refresh_token_store[old_token] = {"revoked": True, "revoked_at": datetime.utcnow()}

    return new_token


def validate_refresh_token(token: str) -> Optional[dict]:
    """Validate refresh token and check if revoked."""
    # Check if revoked
    if token in _refresh_token_store and _refresh_token_store[token].get("revoked"):
        return None

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None
```

### Step 4: Update Refresh Endpoint

```python
# backend/app/auth/routes.py

@router.post("/refresh", response_model=Token)
async def refresh_token(data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Refresh access token with rotation."""
    payload = validate_refresh_token(data.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked refresh token"
        )

    user_id = payload["sub"]
    role = payload["role"]

    # Validate user still exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    token_data = {"sub": user_id, "role": role}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data, old_token=data.refresh_token)
    )
```

### Step 5: Audit Logging

```python
# backend/app/services/audit_service.py

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.database import Base


class AuditLog(Base):
    """Audit log for authentication events."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AuditService:
    EVENT_TYPES = {
        'LOGIN_SUCCESS': 'User logged in successfully',
        'LOGIN_FAILED': 'Login attempt failed',
        'OAUTH_STARTED': 'OAuth flow initiated',
        'OAUTH_SUCCESS': 'OAuth login successful',
        'OAUTH_FAILED': 'OAuth login failed',
        'LOGOUT': 'User logged out',
        'TOKEN_REFRESH': 'Token refreshed',
        'USER_CREATED': 'New user created',
    }

    @staticmethod
    async def log(
        db,
        event_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[str] = None
    ):
        """Log an audit event."""
        log_entry = AuditLog(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        db.add(log_entry)
        await db.commit()
```

### Step 6: Add Audit Logging to OAuth

```python
# backend/app/auth/oauth_routes.py

from app.services.audit_service import AuditService

@router.get("/authorize")
async def oauth_authorize(request: Request, db: AsyncSession = Depends(get_db)):
    """Redirect to Google OAuth authorization page."""
    # Log OAuth start
    await AuditService.log(
        db,
        event_type='OAUTH_STARTED',
        ip_address=request.client.host,
        user_agent=request.headers.get('user-agent')
    )

    # ... rest of implementation ...


@router.get("/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    # ...
):
    # ... after successful login ...

    await AuditService.log(
        db,
        event_type='OAUTH_SUCCESS' if not is_new_user else 'USER_CREATED',
        user_id=str(user.id),
        ip_address=request.client.host,
        user_agent=request.headers.get('user-agent'),
        details=f"Provider: google, Email: {user.email}"
    )

    # ... return response ...

    # On error:
    except Exception as e:
        await AuditService.log(
            db,
            event_type='OAUTH_FAILED',
            ip_address=request.client.host,
            user_agent=request.headers.get('user-agent'),
            details=str(e)
        )
        raise HTTPException(...)
```

### Step 7: Create Audit Log Migration

```python
# Add to migration

def upgrade():
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('details', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'])
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'])
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'])
```

## Todo List

- [ ] Create rate_limit.py middleware
- [ ] Apply rate limiting to OAuth endpoints
- [ ] Update security.py with token rotation
- [ ] Update refresh endpoint with rotation
- [ ] Create audit_service.py
- [ ] Add audit logging to OAuth routes
- [ ] Create audit_logs table migration
- [ ] Test rate limiting works
- [ ] Test token rotation

## Success Criteria

- [ ] Rate limiting blocks after 10 req/min
- [ ] Revoked refresh tokens rejected
- [ ] New refresh token issued on refresh
- [ ] Audit logs created for auth events
- [ ] Audit logs queryable by user/date

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Rate limit too aggressive | Medium | Configurable limits |
| Token store memory leak | Medium | Use Redis with TTL |
| Audit log performance | Low | Async writes, indexed queries |

## Security Considerations

- Rate limiting prevents brute force
- Token rotation prevents replay attacks
- Audit logs enable security monitoring
- IP logging for forensic analysis

## Next Steps

After completion:
- Proceed to Phase 6: Testing & Documentation
- Consider Redis for token store in production
