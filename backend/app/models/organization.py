"""Organization and OrganizationMember models."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, JSON, Index, UniqueConstraint, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.database import Base
from app.models.enums import OrgRole


class Organization(Base):
    """Organization model for multi-tenancy."""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    max_documents = Column(Integer, default=100)
    max_storage_bytes = Column(BigInteger, default=5368709120)  # 5GB
    current_documents = Column(Integer, default=0)
    current_storage_bytes = Column(BigInteger, default=0)
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_organizations")
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="organization", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="organization")
    invitations = relationship("Invitation", back_populates="organization", cascade="all, delete-orphan")


class OrganizationMember(Base):
    """Organization membership with roles."""
    __tablename__ = "organization_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # DB uses VARCHAR(20) with CHECK constraint, not PG native enum
    role = Column(String(20), default=OrgRole.MEMBER.value, nullable=False)
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="organization_memberships")
    invited_by = relationship("User", foreign_keys=[invited_by_id])

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
        Index("ix_org_members_composite", "organization_id", "user_id"),
    )
