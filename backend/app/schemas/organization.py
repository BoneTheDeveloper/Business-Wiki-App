"""Organization and member Pydantic schemas."""
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models.enums import OrgRole
from app.schemas.user import UserResponse


class OrganizationCreate(BaseModel):
    """Organization creation request."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=3, max_length=100, pattern=r"^[a-z0-9-]+$")


class OrganizationUpdate(BaseModel):
    """Organization update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    settings: Optional[dict] = None


class OrganizationResponse(BaseModel):
    """Organization response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    owner_id: UUID
    max_documents: int
    max_storage_bytes: int
    current_documents: int
    current_storage_bytes: int
    settings: dict
    is_active: bool
    created_at: datetime


class OrganizationWithMemberCount(OrganizationResponse):
    """Organization response with member count."""
    member_count: int = 0


class OrganizationMemberCreate(BaseModel):
    """Add member to organization (direct, not via invitation)."""
    user_id: UUID
    role: OrgRole = OrgRole.MEMBER


class OrganizationMemberUpdate(BaseModel):
    """Update member role."""
    role: OrgRole


class OrganizationMemberResponse(BaseModel):
    """Organization member response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    user_id: UUID
    role: OrgRole
    joined_at: datetime
    user: Optional[UserResponse] = None


class InvitationCreate(BaseModel):
    """Create invitation request."""
    invitee_email: EmailStr
    role: OrgRole = OrgRole.MEMBER


class InvitationResponse(BaseModel):
    """Invitation response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    invitee_email: str
    role: OrgRole
    created_at: datetime
    expires_at: datetime
    used: bool


class InvitationAccept(BaseModel):
    """Accept invitation request."""
    token: str


class InvitationList(BaseModel):
    """Paginated invitation list response."""
    items: List[InvitationResponse]
    total: int
