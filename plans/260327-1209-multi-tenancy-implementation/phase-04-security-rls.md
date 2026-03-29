# Phase 4: Security & Row-Level Security (RLS)

**Priority:** Critical
**Duration:** Week 4-5 (3 days)
**Status:** Pending
**Dependencies:** Phase 1, Phase 2, Phase 3

---

## Overview

Implement PostgreSQL Row-Level Security (RLS) policies and application-level security measures for tenant isolation.

### Key Objectives
- Enable RLS on all tenant-scoped tables
- Create secure RLS policies
- Implement application-level permission checks
- Test tenant isolation thoroughly
- Security audit and penetration testing

---

## Requirements

### Security Requirements
- **Tenant Isolation:** Users cannot access other orgs' data
- **Defense in Depth:** RLS + application checks
- **Audit Trail:** Log all access attempts
- **Rate Limiting:** Prevent abuse on invitation endpoints

### Performance Requirements
- RLS adds < 10ms to queries
- Permission checks < 100ms
- No query plan regressions

---

## Architecture

### Security Layers

```
1. Authentication (JWT)
   ↓
2. Application-Level Checks
   ↓
3. PostgreSQL RLS
   ↓
4. Data
```

### RLS Policy Strategy

```sql
-- Pattern: Set user context in session
SET LOCAL app.current_user_id = 'uuid';
SET LOCAL app.current_org_id = 'uuid';

-- RLS policies use context
CREATE POLICY policy_name ON table
    USING (organization_id = current_setting('app.current_org_id')::uuid);
```

---

## Implementation Steps

### Step 1: Enable RLS on Tables (Day 1)

**File:** `backend/app/migrations/versions/XXXX_enable_rls_policies.py`

```python
"""Enable Row-Level Security policies.

Revision ID: XXXX
Revises: Previous
Create Date: 2026-03-27
"""
from alembic import op
from sqlalchemy import text


def upgrade():
    """Enable RLS on tenant-scoped tables."""

    # 1. Create app context setting function
    op.execute(text("""
        CREATE OR REPLACE FUNCTION set_app_config(key text, value text)
        RETURNS void AS $$
        BEGIN
            EXECUTE format('SET LOCAL %s = %L', key, value);
        END;
        $$ LANGUAGE plpgsql;
    """))

    # 2. Enable RLS on documents table
    op.execute(text("ALTER TABLE documents ENABLE ROW LEVEL SECURITY"))

    # 3. Create documents RLS policies

    # Policy: Organization members can see documents in their org
    op.execute(text("""
        CREATE POLICY org_member_document_select ON documents
        FOR SELECT
        USING (
            -- Must be org member
            EXISTS (
                SELECT 1 FROM organization_members om
                WHERE om.organization_id = documents.organization_id
                AND om.user_id = current_setting('app.current_user_id', true)::uuid
            )
            AND (
                -- Public documents: all members can view
                documents.visibility = 'public'
                OR
                -- Restricted documents: must have access grant
                (documents.visibility = 'restricted' AND (
                    -- Direct user access
                    EXISTS (
                        SELECT 1 FROM document_access da
                        WHERE da.document_id = documents.id
                        AND da.user_id = current_setting('app.current_user_id', true)::uuid
                    )
                    OR
                    -- Group-based access
                    EXISTS (
                        SELECT 1 FROM document_access da
                        JOIN group_members gm ON gm.group_id = da.group_id
                        WHERE da.document_id = documents.id
                        AND gm.user_id = current_setting('app.current_user_id', true)::uuid
                    )
                ))
                OR
                -- Private documents: owner or admin only
                (documents.visibility = 'private' AND (
                    documents.user_id = current_setting('app.current_user_id', true)::uuid
                    OR EXISTS (
                        SELECT 1 FROM organization_members om
                        WHERE om.organization_id = documents.organization_id
                        AND om.user_id = current_setting('app.current_user_id', true)::uuid
                        AND om.role IN ('owner', 'admin')
                    )
                ))
            )
        )
    """))

    # Policy: Document modification (owner or admin)
    op.execute(text("""
        CREATE POLICY document_modification ON documents
        FOR ALL
        USING (
            documents.user_id = current_setting('app.current_user_id', true)::uuid
            OR EXISTS (
                SELECT 1 FROM organization_members om
                WHERE om.organization_id = documents.organization_id
                AND om.user_id = current_setting('app.current_user_id', true)::uuid
                AND om.role IN ('owner', 'admin')
            )
        )
    """))

    # 4. Enable RLS on document_chunks table
    op.execute(text("ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY"))

    op.execute(text("""
        CREATE POLICY chunks_follow_document ON document_chunks
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM documents d
                WHERE d.id = document_chunks.document_id
                AND (
                    EXISTS (
                        SELECT 1 FROM organization_members om
                        WHERE om.organization_id = d.organization_id
                        AND om.user_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
            )
        )
    """))

    # 5. Enable RLS on document_access table
    op.execute(text("ALTER TABLE document_access ENABLE ROW LEVEL SECURITY"))

    op.execute(text("""
        CREATE POLICY access_same_org ON document_access
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM documents d
                WHERE d.id = document_access.document_id
                AND EXISTS (
                    SELECT 1 FROM organization_members om
                    WHERE om.organization_id = d.organization_id
                    AND om.user_id = current_setting('app.current_user_id', true)::uuid
                )
            )
        )
    """))

    # 6. Enable RLS on groups table
    op.execute(text("ALTER TABLE groups ENABLE ROW LEVEL SECURITY"))

    op.execute(text("""
        CREATE POLICY groups_same_org ON groups
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM organization_members om
                WHERE om.organization_id = groups.organization_id
                AND om.user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
    """))

    # 7. Enable RLS on group_members table
    op.execute(text("ALTER TABLE group_members ENABLE ROW LEVEL SECURITY"))

    op.execute(text("""
        CREATE POLICY group_members_same_org ON group_members
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM groups g
                WHERE g.id = group_members.group_id
                AND EXISTS (
                    SELECT 1 FROM organization_members om
                    WHERE om.organization_id = g.organization_id
                    AND om.user_id = current_setting('app.current_user_id', true)::uuid
                )
            )
        )
    """))

    # 8. Enable RLS on invitations table
    op.execute(text("ALTER TABLE invitations ENABLE ROW LEVEL SECURITY"))

    op.execute(text("""
        CREATE POLICY invitations_same_org ON invitations
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM organization_members om
                WHERE om.organization_id = invitations.organization_id
                AND om.user_id = current_setting('app.current_user_id', true)::uuid
                AND om.role IN ('owner', 'admin')
            )
        )
    """))

    print("✅ RLS policies enabled successfully")


def downgrade():
    """Disable RLS policies."""
    # Drop policies in reverse order
    op.execute(text("ALTER TABLE invitations DISABLE ROW LEVEL SECURITY"))
    op.execute(text("DROP POLICY IF EXISTS invitations_same_org ON invitations"))

    op.execute(text("ALTER TABLE group_members DISABLE ROW LEVEL SECURITY"))
    op.execute(text("DROP POLICY IF EXISTS group_members_same_org ON group_members"))

    op.execute(text("ALTER TABLE groups DISABLE ROW LEVEL SECURITY"))
    op.execute(text("DROP POLICY IF EXISTS groups_same_org ON groups"))

    op.execute(text("ALTER TABLE document_access DISABLE ROW LEVEL SECURITY"))
    op.execute(text("DROP POLICY IF EXISTS access_same_org ON document_access"))

    op.execute(text("ALTER TABLE document_chunks DISABLE ROW LEVEL SECURITY"))
    op.execute(text("DROP POLICY IF EXISTS chunks_follow_document ON document_chunks"))

    op.execute(text("ALTER TABLE documents DISABLE ROW LEVEL SECURITY"))
    op.execute(text("DROP POLICY IF EXISTS org_member_document_select ON documents"))
    op.execute(text("DROP POLICY IF EXISTS document_modification ON documents"))

    op.execute(text("DROP FUNCTION IF EXISTS set_app_config(text, text)"))

    print("✅ RLS policies disabled")
```

---

### Step 2: Application-Level RLS Context (Day 1)

**File:** `backend/app/api/deps.py` (modify existing)

```python
"""API dependencies with RLS context."""
from typing import Generator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.models.database import AsyncSessionLocal
from app.models.models import User
from app.core.config import settings
from app.core.exceptions import Unauthorized

security = HTTPBearer()


async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_user_with_rls(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user and set RLS context.

    This dependency MUST be used for all endpoints that access tenant-scoped data.
    """
    # Set RLS context variables
    await db.execute(
        text("SET LOCAL app.current_user_id = :user_id"),
        {"user_id": str(current_user.id)}
    )

    # Optionally set org context if user has one
    # This requires fetching user's current org from session or header
    org_id = get_current_org_id()  # Implement this based on your auth flow
    if org_id:
        await db.execute(
            text("SET LOCAL app.current_org_id = :org_id"),
            {"org_id": str(org_id)}
        )

    return current_user


def get_current_org_id() -> str | None:
    """Get current organization ID from request context.

    Implementation depends on how you track current org:
    - From request header: X-Organization-ID
    - From session: session['org_id']
    - From user's default org: user.default_org_id
    """
    # TODO: Implement based on your auth flow
    # Example: from request.headers.get('X-Organization-ID')
    return None


async def get_current_user_with_org(
    org_id: str,
    current_user: User = Depends(get_current_user_with_rls),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, Organization]:
    """Get current user with organization context and permission check."""
    from app.services.permission_service import PermissionService

    # Set org context
    await db.execute(
        text("SET LOCAL app.current_org_id = :org_id"),
        {"org_id": org_id}
    )

    # Check membership
    role = await PermissionService.get_user_role(db, org_id, current_user.id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Get organization
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return current_user, org
```

---

### Step 3: Security Audit Logging (Day 2)

**File:** `backend/app/services/audit_service.py`

```python
"""Audit logging service."""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID
from typing import Optional
import json

from app.models.models import AuditLog


class AuditService:
    """Audit logging for security events."""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        event_type: str,
        user_id: UUID,
        org_id: Optional[UUID],
        details: dict,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log security event."""
        log = AuditLog(
            event_type=event_type,
            user_id=user_id,
            organization_id=org_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow()
        )
        db.add(log)
        await db.commit()

    @staticmethod
    async def log_document_access(
        db: AsyncSession,
        user_id: UUID,
        document_id: UUID,
        action: str,
        granted: bool,
        reason: Optional[str] = None
    ):
        """Log document access attempt."""
        await AuditService.log_event(
            db,
            event_type="document_access",
            user_id=user_id,
            org_id=None,
            details={
                "document_id": str(document_id),
                "action": action,
                "granted": granted,
                "reason": reason
            }
        )

    @staticmethod
    async def log_permission_change(
        db: AsyncSession,
        changed_by: UUID,
        target_user: UUID,
        org_id: UUID,
        old_role: str,
        new_role: str
    ):
        """Log role change."""
        await AuditService.log_event(
            db,
            event_type="permission_change",
            user_id=changed_by,
            org_id=org_id,
            details={
                "target_user": str(target_user),
                "old_role": old_role,
                "new_role": new_role
            }
        )

    @staticmethod
    async def log_invitation_event(
        db: AsyncSession,
        event_type: str,  # invitation_sent, invitation_accepted, invitation_expired
        invited_by: UUID,
        org_id: UUID,
        invitee_email: str,
        token_id: Optional[UUID] = None
    ):
        """Log invitation events."""
        await AuditService.log_event(
            db,
            event_type=event_type,
            user_id=invited_by,
            org_id=org_id,
            details={
                "invitee_email": invitee_email,
                "token_id": str(token_id) if token_id else None
            }
        )

    @staticmethod
    async def log_tenant_isolation_violation(
        db: AsyncSession,
        user_id: UUID,
        attempted_org_id: UUID,
        resource_type: str,
        resource_id: UUID
    ):
        """Log attempted tenant isolation violation (CRITICAL)."""
        await AuditService.log_event(
            db,
            event_type="tenant_isolation_violation",
            user_id=user_id,
            org_id=attempted_org_id,
            details={
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "severity": "critical"
            }
        )

        # Also log to separate security alerts
        print(f"🚨 SECURITY ALERT: Tenant isolation violation by user {user_id}")
```

---

### Step 4: Rate Limiting (Day 2)

**File:** `backend/app/middleware/rate_limiter.py`

```python
"""Rate limiting middleware."""
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_value
from slowapi.util import get_remote_address
from typing import Callable

limiter = Limiter(key_func=get_remote_address)


def rate_limit(
    limit: str = "5/minute",
    key_func: Callable = None
):
    """Rate limit decorator.

    Usage:
        @rate_limit("5/hour")
        async def invite_member(...):
            ...
    """
    def decorator(func):
        return limiter.limit(limit)(func)
    return decorator


# Custom rate limiters
invitation_rate_limit = rate_limit("5/hour")  # 5 invitations per hour per org
document_upload_rate_limit = rate_limit("10/minute")  # 10 uploads per minute
search_rate_limit = rate_limit("30/minute")  # 30 searches per minute
```

**Usage in routes:**

```python
# backend/app/api/v1/routes/organizations.py

from app.middleware.rate_limiter import invitation_rate_limit

@router.post("/{org_id}/invite")
@invitation_rate_limit
async def invite_member(
    org_id: UUID,
    invitation_data: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Invite member with rate limiting."""
    # Implementation
    pass
```

---

### Step 5: Security Testing (Day 3)

**File:** `backend/tests/security/test_tenant_isolation.py`

```python
"""Security tests for tenant isolation."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.models import User, Organization, Document, OrganizationMember
from app.services.permission_service import PermissionService
from app.services.organization_service import OrganizationService


@pytest.mark.asyncio
async def test_user_cannot_access_other_org_documents(db_session):
    """Test RLS prevents cross-tenant document access."""
    # Create two users
    user1 = User(email="user1@test.com", password_hash="hash", role="user")
    user2 = User(email="user2@test.com", password_hash="hash", role="user")
    db_session.add_all([user1, user2])
    await db_session.commit()

    # Create organizations
    org1 = Organization(
        name="Org 1",
        slug="org-1",
        owner_id=user1.id
    )
    org2 = Organization(
        name="Org 2",
        slug="org-2",
        owner_id=user2.id
    )
    db_session.add_all([org1, org2])
    await db_session.commit()

    # Add members
    member1 = OrganizationMember(
        organization_id=org1.id,
        user_id=user1.id,
        role="owner"
    )
    member2 = OrganizationMember(
        organization_id=org2.id,
        user_id=user2.id,
        role="owner"
    )
    db_session.add_all([member1, member2])
    await db_session.commit()

    # Create document in org1
    doc1 = Document(
        user_id=user1.id,
        organization_id=org1.id,
        filename="secret.pdf",
        file_path="/docs/secret.pdf",
        visibility="private"
    )
    db_session.add(doc1)
    await db_session.commit()

    # Set RLS context for user2
    await db_session.execute(
        text("SET LOCAL app.current_user_id = :user_id"),
        {"user_id": str(user2.id)}
    )

    # Try to access document (should fail with RLS)
    result = await db_session.execute(
        select(Document).where(Document.id == doc1.id)
    )
    doc = result.scalar_one_or_none()

    # RLS should prevent access
    assert doc is None, "RLS failed: User2 can see User1's document"


@pytest.mark.asyncio
async def test_rls_with_public_document(db_session):
    """Test that public documents are accessible to org members."""
    user1 = User(email="user1@test.com", password_hash="hash", role="user")
    user2 = User(email="user2@test.com", password_hash="hash", role="user")
    db_session.add_all([user1, user2])
    await db_session.commit()

    # Create org with both users
    org = Organization(name="Test Org", slug="test-org", owner_id=user1.id)
    db_session.add(org)
    await db_session.commit()

    member1 = OrganizationMember(org_id=org.id, user_id=user1.id, role="owner")
    member2 = OrganizationMember(org_id=org.id, user_id=user2.id, role="member")
    db_session.add_all([member1, member2])
    await db_session.commit()

    # Create public document
    doc = Document(
        user_id=user1.id,
        organization_id=org.id,
        filename="public.pdf",
        file_path="/docs/public.pdf",
        visibility="public"
    )
    db_session.add(doc)
    await db_session.commit()

    # Set RLS context for user2
    await db_session.execute(
        text("SET LOCAL app.current_user_id = :user_id"),
        {"user_id": str(user2.id)}
    )

    # Try to access (should succeed)
    result = await db_session.execute(
        select(Document).where(Document.id == doc.id)
    )
    accessible_doc = result.scalar_one_or_none()

    assert accessible_doc is not None, "RLS blocked access to public document"
    assert accessible_doc.visibility == "public"


@pytest.mark.asyncio
async def test_permission_service_document_access(db_session):
    """Test permission service correctly checks document access."""
    user1 = User(email="user1@test.com", password_hash="hash", role="user")
    user2 = User(email="user2@test.com", password_hash="hash", role="user")
    db_session.add_all([user1, user2])
    await db_session.commit()

    org = Organization(name="Test Org", slug="test-org", owner_id=user1.id)
    db_session.add(org)
    await db_session.commit()

    member1 = OrganizationMember(org_id=org.id, user_id=user1.id, role="owner")
    member2 = OrganizationMember(org_id=org.id, user_id=user2.id, role="viewer")
    db_session.add_all([member1, member2])
    await db_session.commit()

    # Private document
    private_doc = Document(
        user_id=user1.id,
        organization_id=org.id,
        filename="private.pdf",
        file_path="/docs/private.pdf",
        visibility="private"
    )
    db_session.add(private_doc)
    await db_session.commit()

    # User2 should NOT have access to private doc
    has_access = await PermissionService.can_access_document(
        db_session, private_doc, user2.id, "view"
    )
    assert has_access is False, "Viewer can access private document"

    # User1 (owner) should have access
    has_access = await PermissionService.can_access_document(
        db_session, private_doc, user1.id, "view"
    )
    assert has_access is True, "Owner cannot access private document"


@pytest.mark.asyncio
async def test_group_based_document_access(db_session):
    """Test group-based document access control."""
    # Setup users and org
    user1 = User(email="user1@test.com", password_hash="hash", role="user")
    user2 = User(email="user2@test.com", password_hash="hash", role="user")
    user3 = User(email="user3@test.com", password_hash="hash", role="user")
    db_session.add_all([user1, user2, user3])
    await db_session.commit()

    org = Organization(name="Test Org", slug="test-org", owner_id=user1.id)
    db_session.add(org)
    await db_session.commit()

    for user in [user1, user2, user3]:
        db_session.add(OrganizationMember(
            org_id=org.id, user_id=user.id, role="member"
        ))
    await db_session.commit()

    # Create group with user2
    group = Group(
        organization_id=org.id,
        name="Engineering",
        created_by_id=user1.id
    )
    db_session.add(group)
    await db_session.commit()

    db_session.add(GroupMember(group_id=group.id, user_id=user2.id))
    await db_session.commit()

    # Create restricted document with group access
    doc = Document(
        user_id=user1.id,
        organization_id=org.id,
        filename="restricted.pdf",
        file_path="/docs/restricted.pdf",
        visibility="restricted"
    )
    db_session.add(doc)
    await db_session.commit()

    # Grant group access
    db_session.add(DocumentAccess(
        document_id=doc.id,
        group_id=group.id,
        access_level="view"
    ))
    await db_session.commit()

    # Test access
    # User2 (in group) should have access
    assert await PermissionService.can_access_document(
        db_session, doc, user2.id, "view"
    ) is True

    # User3 (not in group) should NOT have access
    assert await PermissionService.can_access_document(
        db_session, doc, user3.id, "view"
    ) is False


@pytest.mark.asyncio
async def test_rate_limiting_on_invitations(db_session, client):
    """Test invitation rate limiting."""
    # Setup
    user = User(email="test@test.com", password_hash="hash", role="user")
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Test", slug="test", owner_id=user.id)
    db_session.add(org)
    await db_session.commit()

    # Get auth token
    token = create_test_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Send 6 invitations (limit is 5/hour)
    for i in range(6):
        response = await client.post(
            f"/api/v1/organizations/{org.id}/invite",
            json={"email": f"user{i}@test.com", "role": "member"},
            headers=headers
        )

        if i < 5:
            assert response.status_code == 201
        else:
            assert response.status_code == 429  # Too Many Requests
```

---

### Step 6: Security Audit Checklist (Day 3)

**File:** `backend/tests/security/SECURITY_AUDIT_CHECKLIST.md`

```markdown
# Security Audit Checklist

## Pre-Deployment Security Checks

### Authentication & Authorization
- [ ] JWT tokens expire after 30 minutes
- [ ] Password hashing uses bcrypt with 12 salt rounds
- [ ] Token refresh mechanism works
- [ ] Invalid tokens return 401
- [ ] Expired tokens return 401
- [ ] Rate limiting on login endpoint (5/minute)

### Tenant Isolation (CRITICAL)
- [ ] RLS enabled on all tenant-scoped tables
- [ ] RLS context set before every query
- [ ] Cross-tenant document access blocked
- [ ] Cross-tenant group access blocked
- [ ] Cross-tenant member list access blocked
- [ ] Admin cannot access other orgs' data
- [ ] Owner cannot access other orgs' data

### Document Access Control
- [ ] Public documents visible to all org members
- [ ] Restricted documents require access grant
- [ ] Private documents visible to owner + admins only
- [ ] Document access grants work for users
- [ ] Document access grants work for groups
- [ ] Access revocation works immediately

### Invitation Security
- [ ] Tokens are one-time use
- [ ] Tokens expire after 7 days
- [ ] Tokens are salted and hashed
- [ ] Used tokens cannot be reused
- [ ] Expired tokens cannot be used
- [ ] Rate limiting on invitations (5/hour/org)

### Input Validation
- [ ] All API inputs validated with Pydantic
- [ ] Email format validated
- [ ] Organization slug format validated (alphanumeric + hyphens)
- [ ] File size limits enforced (50MB)
- [ ] File type validation (PDF, DOCX, XLSX only)
- [ ] SQL injection prevention (parameterized queries)

### Data Protection
- [ ] API keys never logged
- [ ] Passwords never logged
- [ ] Sensitive data encrypted at rest (future)
- [ ] HTTPS enforced in production
- [ ] CORS configured correctly

### Audit Logging
- [ ] All permission changes logged
- [ ] All invitation events logged
- [ ] All document access attempts logged
- [ ] Tenant isolation violations logged with severity

### Performance
- [ ] RLS adds < 10ms to queries
- [ ] Permission checks < 100ms
- [ ] No N+1 queries on permission checks
- [ ] Proper indexes on all filtered columns

## Penetration Testing

### Manual Testing
1. **Tenant Isolation:**
   - Create 2 users, 2 orgs
   - Upload document in org1
   - Try to access with user2 (should fail)
   - Try direct API call with user2's token (should fail)

2. **Token Security:**
   - Use same invitation token twice (should fail)
   - Use expired token (should fail)
   - Tamper with token (should fail)

3. **Permission Escalation:**
   - Member tries to invite (should fail)
   - Viewer tries to upload (should fail)
   - Member tries to change roles (should fail)

### Automated Testing
- Run all security tests: `pytest tests/security/ -v`
- Run SQL injection tests: `pytest tests/security/test_sql_injection.py`
- Run XSS tests: `pytest tests/security/test_xss.py`

## Rollback Plan

If critical security issue found:
1. Disable RLS immediately: `ALTER TABLE documents DISABLE ROW LEVEL SECURITY`
2. Rely on application-level checks temporarily
3. Investigate and fix issue
4. Re-enable RLS after fix
5. Run full security test suite
```

---

## Testing Checklist

- [ ] RLS policies enabled on all tables
- [ ] Cross-tenant access blocked
- [ ] Application-level checks working
- [ ] Rate limiting enforced
- [ ] Audit logging working
- [ ] Security tests pass (100%)
- [ ] Performance tests pass (RLS < 10ms)
- [ ] Penetration testing complete

---

## Next Phase

→ [Phase 5: Testing & Deployment](./phase-05-testing-deployment.md)
