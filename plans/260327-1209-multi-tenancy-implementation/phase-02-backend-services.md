# Phase 2: Backend Services & API

**Priority:** Critical
**Duration:** Week 2-3 (10 days)
**Status:** Pending
**Dependencies:** Phase 1 (Database Migration)

---

## Overview

Implement backend services, API endpoints, and business logic for multi-tenancy features.

### Key Objectives
- Organization CRUD operations
- Member invitation system
- Group management
- Document access control
- Permission checking services
- Quota management

---

## Requirements

### Functional Requirements
- Users can create organizations
- Owners/admins can invite members via email
- Members can accept invitations
- Groups can be created and managed
- Document visibility can be controlled
- Quotas are enforced server-side

### Non-Functional Requirements
- API response time < 500ms
- Email delivery < 5 seconds
- Permission checks < 100ms
- Rate limiting on invitations (5/hour/org)

---

## Architecture

### Service Layer

```
API Routes
    ↓
Service Layer
    ├─ OrganizationService
    ├─ InvitationService
    ├─ PermissionService
    ├─ GroupService
    ├─ QuotaService
    └─ DocumentAccessService
    ↓
Data Layer (ORM Models)
```

### Permission Flow

```
Request → Auth Middleware → Permission Check → Business Logic → Response
              ↓
         Set RLS Context
```

---

## Implementation Steps

### Step 1: Pydantic Schemas (Day 1)

**File:** `backend/app/schemas/organization.py`

```python
"""Organization schemas."""
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID
from typing import Optional, List


class OrganizationCreate(BaseModel):
    """Create organization request."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=3, max_length=100, pattern="^[a-z0-9-]+$")

    @validator('slug')
    def slug_format(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug must contain only letters, numbers, hyphens, underscores')
        if v.startswith('-') or v.endswith('-'):
            raise ValueError('Slug cannot start or end with hyphen')
        return v.lower()


class OrganizationUpdate(BaseModel):
    """Update organization request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    settings: Optional[dict] = None


class OrganizationResponse(BaseModel):
    """Organization response."""
    id: UUID
    name: str
    slug: str
    owner_id: UUID

    # Quotas
    max_documents: int
    max_storage_bytes: int
    current_documents: int
    current_storage_bytes: int

    settings: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationMemberCreate(BaseModel):
    """Add member to organization."""
    user_id: Optional[UUID] = None
    email: Optional[str] = None  # Alternative to user_id
    role: str = Field(..., pattern="^(admin|member|viewer)$")


class OrganizationMemberUpdate(BaseModel):
    """Update member role."""
    role: str = Field(..., pattern="^(admin|member|viewer)$")


class OrganizationMemberResponse(BaseModel):
    """Organization member response."""
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: str
    invited_by_id: Optional[UUID]
    joined_at: datetime

    # User details (populated from relationship)
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


class InvitationCreate(BaseModel):
    """Create invitation request."""
    email: str = Field(..., max_length=255)
    role: str = Field(..., pattern="^(admin|member|viewer)$")


class InvitationResponse(BaseModel):
    """Invitation response."""
    id: UUID
    organization_id: UUID
    organization_name: str
    invitee_email: str
    role: str
    invited_by_id: UUID
    created_at: datetime
    expires_at: datetime
    used: bool

    class Config:
        from_attributes = True


class AcceptInvitation(BaseModel):
    """Accept invitation request."""
    token: str


class GroupCreate(BaseModel):
    """Create group request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class GroupUpdate(BaseModel):
    """Update group request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class GroupResponse(BaseModel):
    """Group response."""
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str]
    created_by_id: Optional[UUID]
    created_at: datetime
    member_count: int = 0

    class Config:
        from_attributes = True


class GroupMemberAdd(BaseModel):
    """Add member to group."""
    user_id: UUID


class DocumentAccessGrant(BaseModel):
    """Grant document access."""
    user_id: Optional[UUID] = None
    group_id: Optional[UUID] = None
    access_level: str = Field(..., pattern="^(view|edit)$")

    @validator('group_id', always=True)
    def check_target(cls, v, values):
        if not v and not values.get('user_id'):
            raise ValueError('Either user_id or group_id must be provided')
        if v and values.get('user_id'):
            raise ValueError('Only one of user_id or group_id can be provided')
        return v


class DocumentAccessResponse(BaseModel):
    """Document access response."""
    id: UUID
    document_id: UUID
    user_id: Optional[UUID]
    group_id: Optional[UUID]
    access_level: str
    granted_by_id: Optional[UUID]
    granted_at: datetime

    class Config:
        from_attributes = True
```

---

### Step 2: Organization Service (Day 2)

**File:** `backend/app/services/organization_service.py`

```python
"""Organization business logic."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.models.models import (
    Organization, OrganizationMember, User, Document
)
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.core.exceptions import (
    OrganizationNotFound,
    PermissionDenied,
    SlugAlreadyExists,
    QuotaExceeded
)


class OrganizationService:
    """Organization management service."""

    @staticmethod
    async def create_organization(
        db: AsyncSession,
        owner: User,
        org_data: OrganizationCreate
    ) -> Organization:
        """Create new organization with owner as member."""
        # Check slug uniqueness
        existing = await db.execute(
            select(Organization).where(Organization.slug == org_data.slug)
        )
        if existing.scalar_one_or_none():
            raise SlugAlreadyExists(f"Slug '{org_data.slug}' already exists")

        # Create organization
        org = Organization(
            name=org_data.name,
            slug=org_data.slug,
            owner_id=owner.id,
            max_documents=100,
            max_storage_bytes=5368709120,  # 5GB
            current_documents=0,
            current_storage_bytes=0,
            settings={},
            is_active=True
        )
        db.add(org)
        await db.flush()

        # Add owner as member
        member = OrganizationMember(
            organization_id=org.id,
            user_id=owner.id,
            role="owner",
            joined_at=datetime.utcnow()
        )
        db.add(member)
        await db.commit()
        await db.refresh(org)

        return org

    @staticmethod
    async def get_organization(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID
    ) -> Organization:
        """Get organization by ID with permission check."""
        org = await db.get(Organization, org_id)
        if not org:
            raise OrganizationNotFound(f"Organization {org_id} not found")

        # Check membership
        member = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id
            )
        )
        if not member.scalar_one_or_none():
            raise PermissionDenied("You are not a member of this organization")

        return org

    @staticmethod
    async def update_organization(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID,
        update_data: OrganizationUpdate
    ) -> Organization:
        """Update organization settings (owner only)."""
        org = await OrganizationService.get_organization(db, org_id, user_id)

        # Check owner permission
        if org.owner_id != user_id:
            raise PermissionDenied("Only organization owner can update settings")

        # Update fields
        if update_data.name is not None:
            org.name = update_data.name
        if update_data.settings is not None:
            org.settings = update_data.settings

        org.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(org)

        return org

    @staticmethod
    async def get_user_organizations(
        db: AsyncSession,
        user_id: UUID
    ) -> List[Organization]:
        """Get all organizations user is member of."""
        result = await db.execute(
            select(Organization)
            .join(OrganizationMember)
            .where(OrganizationMember.user_id == user_id)
            .options(selectinload(Organization.owner))
        )
        return result.scalars().all()

    @staticmethod
    async def delete_organization(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID
    ) -> None:
        """Delete organization (owner only)."""
        org = await OrganizationService.get_organization(db, org_id, user_id)

        if org.owner_id != user_id:
            raise PermissionDenied("Only organization owner can delete organization")

        # Soft delete (mark as inactive)
        org.is_active = False
        org.updated_at = datetime.utcnow()
        await db.commit()

    @staticmethod
    async def get_organization_stats(
        db: AsyncSession,
        org_id: UUID
    ) -> dict:
        """Get organization statistics."""
        # Member count
        member_count = await db.execute(
            select(func.count(OrganizationMember.id))
            .where(OrganizationMember.organization_id == org_id)
        )

        # Document count
        doc_count = await db.execute(
            select(func.count(Document.id))
            .where(Document.organization_id == org_id)
        )

        # Storage used
        storage_used = await db.execute(
            select(func.sum(Document.file_size))
            .where(Document.organization_id == org_id)
        )

        return {
            "member_count": member_count.scalar() or 0,
            "document_count": doc_count.scalar() or 0,
            "storage_bytes": storage_used.scalar() or 0
        }
```

---

### Step 3: Invitation Service (Day 3)

**File:** `backend/app/services/invitation_service.py`

```python
"""Invitation management service."""
import secrets
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.models.models import Invitation, Organization, OrganizationMember, User
from app.schemas.organization import InvitationCreate
from app.core.exceptions import (
    InvitationNotFound,
    InvitationExpired,
    InvitationAlreadyUsed,
    UserAlreadyMember,
    PermissionDenied
)
from app.services.email_service import EmailService


class InvitationService:
    """Invitation handling service."""

    @staticmethod
    def generate_token(email: str) -> tuple[str, str]:
        """Generate secure invitation token.

        Returns:
            tuple: (token_hash, token_salt)
        """
        random_bytes = secrets.token_bytes(32)
        salt = secrets.token_hex(32)
        token_hash = hashlib.sha256(
            random_bytes + salt.encode() + email.encode()
        ).hexdigest()
        return token_hash, salt

    @staticmethod
    async def create_invitation(
        db: AsyncSession,
        org_id: UUID,
        invited_by: User,
        invitation_data: InvitationCreate,
        email_service: EmailService
    ) -> Invitation:
        """Create and send invitation."""
        # Check if user is already a member
        existing_user = await db.execute(
            select(User).where(User.email == invitation_data.email)
        )
        user = existing_user.scalar_one_or_none()

        if user:
            # Check membership
            member = await db.execute(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.user_id == user.id
                )
            )
            if member.scalar_one_or_none():
                raise UserAlreadyMember("User is already a member of this organization")

        # Generate token
        token_hash, token_salt = InvitationService.generate_token(invitation_data.email)

        # Create invitation
        invitation = Invitation(
            organization_id=org_id,
            invitee_email=invitation_data.email,
            role=invitation_data.role,
            token_hash=token_hash,
            token_salt=token_salt,
            invited_by_id=invited_by.id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            used=False
        )
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)

        # Send email
        org = await db.get(Organization, org_id)
        invite_link = f"{settings.FRONTEND_URL}/invitations/{token_hash}/accept"

        await email_service.send_invitation_email(
            to_email=invitation_data.email,
            organization_name=org.name,
            invited_by_name=invited_by.email,
            role=invitation_data.role,
            invite_link=invite_link
        )

        return invitation

    @staticmethod
    async def accept_invitation(
        db: AsyncSession,
        token_hash: str,
        user: User
    ) -> Organization:
        """Accept invitation and join organization."""
        # Get invitation
        invitation = await db.execute(
            select(Invitation).where(Invitation.token_hash == token_hash)
        )
        invitation = invitation.scalar_one_or_none()

        if not invitation:
            raise InvitationNotFound("Invitation not found")

        if invitation.used:
            raise InvitationAlreadyUsed("Invitation has already been used")

        if invitation.expires_at < datetime.utcnow():
            raise InvitationExpired("Invitation has expired")

        # Check email match
        if user.email != invitation.invitee_email:
            raise PermissionDenied(
                f"This invitation is for {invitation.invitee_email}, "
                f"but you are logged in as {user.email}"
            )

        # Check if already member
        existing = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == invitation.organization_id,
                OrganizationMember.user_id == user.id
            )
        )
        if existing.scalar_one_or_none():
            raise UserAlreadyMember("You are already a member of this organization")

        # Create membership
        member = OrganizationMember(
            organization_id=invitation.organization_id,
            user_id=user.id,
            role=invitation.role,
            invited_by_id=invitation.invited_by_id,
            joined_at=datetime.utcnow()
        )
        db.add(member)

        # Mark invitation as used
        invitation.used = True
        invitation.used_at = datetime.utcnow()

        await db.commit()

        # Return organization
        org = await db.get(Organization, invitation.organization_id)
        return org

    @staticmethod
    async def get_pending_invitations(
        db: AsyncSession,
        org_id: UUID
    ) -> list[Invitation]:
        """Get pending invitations for organization."""
        result = await db.execute(
            select(Invitation)
            .where(
                Invitation.organization_id == org_id,
                Invitation.used == False,
                Invitation.expires_at > datetime.utcnow()
            )
            .order_by(Invitation.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def cancel_invitation(
        db: AsyncSession,
        invitation_id: UUID,
        user_id: UUID
    ) -> None:
        """Cancel pending invitation."""
        invitation = await db.get(Invitation, invitation_id)
        if not invitation:
            raise InvitationNotFound("Invitation not found")

        # Check permission (admin or inviter)
        org = await db.get(Organization, invitation.organization_id)
        member = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == invitation.organization_id,
                OrganizationMember.user_id == user_id
            )
        )
        member = member.scalar_one_or_none()

        if not member or member.role not in ["owner", "admin"]:
            if invitation.invited_by_id != user_id:
                raise PermissionDenied("You don't have permission to cancel this invitation")

        await db.delete(invitation)
        await db.commit()
```

---

### Step 4: Permission Service (Day 4)

**File:** `backend/app/services/permission_service.py`

```python
"""Permission checking service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID

from app.models.models import (
    Organization, OrganizationMember, Document, DocumentAccess, Group, GroupMember
)
from app.core.exceptions import PermissionDenied


class PermissionService:
    """Permission checking service."""

    @staticmethod
    async def get_user_role(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID
    ) -> Optional[str]:
        """Get user's role in organization."""
        result = await db.execute(
            select(OrganizationMember.role).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def check_organization_permission(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID,
        required_roles: list[str]
    ) -> bool:
        """Check if user has required role in organization."""
        role = await PermissionService.get_user_role(db, org_id, user_id)
        return role in required_roles

    @staticmethod
    async def can_access_document(
        db: AsyncSession,
        document: Document,
        user_id: UUID,
        required_level: str = "view"
    ) -> bool:
        """Check if user can access document.

        Args:
            document: Document to check access for
            user_id: User requesting access
            required_level: "view" or "edit"

        Returns:
            bool: True if user has access
        """
        # 1. Get organization
        org = await db.get(Organization, document.organization_id)
        if not org:
            return False

        # 2. Check if user is owner/admin
        role = await PermissionService.get_user_role(org.id, user_id)
        if role == "owner":
            return True
        if role == "admin":
            return True

        # 3. Check if user is document owner
        if document.user_id == user_id:
            return True

        # 4. Check visibility rules
        if document.visibility == "public":
            # All org members can view public docs
            if required_level == "view":
                return role is not None
            # Only owner can edit public docs
            return False

        elif document.visibility == "restricted":
            # Check explicit access grants
            access = await db.execute(
                select(DocumentAccess).where(
                    DocumentAccess.document_id == document.id,
                    DocumentAccess.user_id == user_id
                )
            )
            user_access = access.scalar_one_or_none()

            if user_access:
                if required_level == "view":
                    return True
                return user_access.access_level == "edit"

            # Check group-based access
            user_groups = await db.execute(
                select(GroupMember.group_id).where(
                    GroupMember.user_id == user_id
                )
            )
            group_ids = [g[0] for g in user_groups.fetchall()]

            if group_ids:
                group_access = await db.execute(
                    select(DocumentAccess).where(
                        DocumentAccess.document_id == document.id,
                        DocumentAccess.group_id.in_(group_ids)
                    )
                )
                for access in group_access.scalars().all():
                    if required_level == "view":
                        return True
                    if access.access_level == "edit":
                        return True

            return False

        else:  # private
            # Only uploader + admins (checked above)
            return False

    @staticmethod
    async def require_organization_role(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID,
        required_roles: list[str]
    ) -> str:
        """Require organization role or raise exception.

        Raises:
            PermissionDenied: If user doesn't have required role

        Returns:
            str: User's role
        """
        role = await PermissionService.get_user_role(db, org_id, user_id)
        if role not in required_roles:
            raise PermissionDenied(
                f"Permission denied. Required roles: {required_roles}"
            )
        return role

    @staticmethod
    async def require_document_access(
        db: AsyncSession,
        document: Document,
        user_id: UUID,
        required_level: str = "view"
    ) -> None:
        """Require document access or raise exception.

        Raises:
            PermissionDenied: If user doesn't have access
        """
        has_access = await PermissionService.can_access_document(
            db, document, user_id, required_level
        )
        if not has_access:
            raise PermissionDenied(
                f"You don't have {required_level} access to this document"
            )
```

---

### Step 5: API Routes (Day 5-7)

**File:** `backend/app/api/v1/routes/organizations.py`

```python
"""Organization API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.models.database import get_db
from app.models.models import User
from app.api.deps import get_current_user
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationMemberCreate,
    OrganizationMemberUpdate,
    OrganizationMemberResponse
)
from app.services.organization_service import OrganizationService
from app.services.permission_service import PermissionService
from app.core.exceptions import OrganizationNotFound, PermissionDenied

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new organization."""
    return await OrganizationService.create_organization(db, current_user, org_data)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get organization by ID."""
    return await OrganizationService.get_organization(db, org_id, current_user.id)


@router.get("/", response_model=List[OrganizationResponse])
async def list_user_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List user's organizations."""
    return await OrganizationService.get_user_organizations(db, current_user.id)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: UUID,
    update_data: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update organization settings."""
    return await OrganizationService.update_organization(
        db, org_id, current_user.id, update_data
    )


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete organization (owner only)."""
    await OrganizationService.delete_organization(db, org_id, current_user.id)


@router.get("/{org_id}/members", response_model=List[OrganizationMemberResponse])
async def list_organization_members(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List organization members."""
    # Check membership
    await PermissionService.require_organization_role(
        db, org_id, current_user.id, ["owner", "admin", "member", "viewer"]
    )

    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org_id)
        .options(selectinload(OrganizationMember.user))
    )
    members = result.scalars().all()

    # Populate user details
    for member in members:
        member.user_email = member.user.email
        member.user_name = member.user.name

    return members


@router.post("/{org_id}/invite", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    org_id: UUID,
    invitation_data: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Invite member to organization."""
    # Check permission (owner or admin)
    await PermissionService.require_organization_role(
        db, org_id, current_user.id, ["owner", "admin"]
    )

    return await InvitationService.create_invitation(
        db, org_id, current_user, invitation_data, email_service
    )


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove member from organization."""
    # Check permission (owner or admin)
    await PermissionService.require_organization_role(
        db, org_id, current_user.id, ["owner", "admin"]
    )

    # Get member
    member = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id
        )
    )
    member = member.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Cannot remove owner
    org = await db.get(Organization, org_id)
    if org.owner_id == user_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove organization owner. Transfer ownership first."
        )

    await db.delete(member)
    await db.commit()
```

**File:** `backend/app/api/v1/routes/invitations.py`

```python
"""Invitation API routes."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.database import get_db
from app.models.models import User
from app.api.deps import get_current_user
from app.schemas.organization import AcceptInvitation, InvitationResponse
from app.services.invitation_service import InvitationService

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post("/{token}/accept", response_model=OrganizationResponse)
async def accept_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept invitation to join organization."""
    return await InvitationService.accept_invitation(db, token, current_user)


@router.get("/{invitation_id}", response_model=InvitationResponse)
async def get_invitation(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get invitation details."""
    # Implementation
    pass


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel pending invitation."""
    await InvitationService.cancel_invitation(db, invitation_id, current_user.id)
```

---

### Step 6: Update Document Routes (Day 8)

**File:** `backend/app/api/v1/routes/documents.py` (modify existing)

```python
# Add to existing document routes

@router.post("/{doc_id}/access", response_model=DocumentAccessResponse)
async def grant_document_access(
    doc_id: UUID,
    access_data: DocumentAccessGrant,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_rls)
):
    """Grant document access to user or group."""
    # Get document
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check permission (owner or admin)
    await PermissionService.require_document_access(
        db, doc, current_user.id, "edit"
    )

    # Create access grant
    access = DocumentAccess(
        document_id=doc_id,
        user_id=access_data.user_id,
        group_id=access_data.group_id,
        access_level=access_data.access_level,
        granted_by_id=current_user.id
    )
    db.add(access)
    await db.commit()
    await db.refresh(access)

    return access


@router.delete("/{doc_id}/access/{access_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_document_access(
    doc_id: UUID,
    access_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_rls)
):
    """Revoke document access."""
    # Get document
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check permission (owner or admin)
    await PermissionService.require_document_access(
        db, doc, current_user.id, "edit"
    )

    # Get access record
    access = await db.get(DocumentAccess, access_id)
    if not access or access.document_id != doc_id:
        raise HTTPException(status_code=404, detail="Access record not found")

    await db.delete(access)
    await db.commit()


@router.patch("/{doc_id}/visibility")
async def update_document_visibility(
    doc_id: UUID,
    visibility: str = Query(..., pattern="^(public|restricted|private)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_rls)
):
    """Update document visibility."""
    # Get document
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check permission (owner or admin)
    await PermissionService.require_document_access(
        db, doc, current_user.id, "edit"
    )

    # Update visibility
    doc.visibility = visibility
    doc.updated_at = datetime.utcnow()

    # Clear access list if changing to private
    if visibility == "private":
        await db.execute(
            delete(DocumentAccess).where(DocumentAccess.document_id == doc_id)
        )

    await db.commit()
    return {"message": "Visibility updated", "visibility": visibility}
```

---

## Testing Checklist

- [ ] Organization CRUD operations work
- [ ] Member invitation flow complete
- [ ] Invitation acceptance works
- [ ] Permission checks enforce roles correctly
- [ ] Document access control works
- [ ] Quota enforcement prevents uploads
- [ ] API endpoints return correct responses
- [ ] Error handling works properly
- [ ] Rate limiting on invitations
- [ ] Email sending works

---

## Next Phase

→ [Phase 3: Frontend Implementation](./phase-03-frontend-implementation.md)
