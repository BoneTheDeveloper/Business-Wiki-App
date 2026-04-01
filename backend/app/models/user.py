"""User model -- synced from Supabase Auth via DB trigger."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime
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
    email_verified = Column(Boolean, nullable=True)
    name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    # DB uses VARCHAR(20) with CHECK constraint, not PG native enum
    role = Column(String(20), default=UserRole.USER.value, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="user")
    owned_organizations = relationship(
        "Organization", foreign_keys="Organization.owner_id", back_populates="owner",
    )
    organization_memberships = relationship(
        "OrganizationMember", foreign_keys="OrganizationMember.user_id",
        back_populates="user", cascade="all, delete-orphan",
    )
    group_memberships = relationship(
        "GroupMember", foreign_keys="GroupMember.user_id",
        back_populates="user", cascade="all, delete-orphan",
    )
    social_accounts = relationship(
        "SocialAccount", foreign_keys="SocialAccount.user_id",
        back_populates="user", cascade="all, delete-orphan",
    )
