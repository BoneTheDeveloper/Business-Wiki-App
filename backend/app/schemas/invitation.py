"""Invitation Pydantic schemas."""
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import List
from datetime import datetime
from uuid import UUID
from app.models.enums import OrgRole


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
