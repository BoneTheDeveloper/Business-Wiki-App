"""Group and group member Pydantic schemas."""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.schemas.user import UserResponse


class GroupCreate(BaseModel):
    """Group creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class GroupUpdate(BaseModel):
    """Group update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class GroupResponse(BaseModel):
    """Group response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str]
    created_at: datetime


class GroupWithMemberCount(GroupResponse):
    """Group response with member count."""
    member_count: int = 0


class GroupMemberAdd(BaseModel):
    """Add member to group request."""
    user_id: UUID


class GroupMemberResponse(BaseModel):
    """Group member response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    user_id: UUID
    added_at: datetime
    user: Optional[UserResponse] = None
