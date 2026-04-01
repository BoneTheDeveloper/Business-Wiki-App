"""User-related Pydantic schemas."""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.enums import UserRole


class UserResponse(BaseModel):
    """User response schema -- returned by /auth/me and admin endpoints."""
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
    """User update request (admin only)."""
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
