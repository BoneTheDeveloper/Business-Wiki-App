"""Group and GroupMember models."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.database import Base


class Group(Base):
    """Document access groups."""
    __tablename__ = "groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    created_by = relationship("User")
    document_access = relationship("DocumentAccess", back_populates="group")

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_org_group_name"),
    )


class GroupMember(Base):
    """Group membership."""
    __tablename__ = "group_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    added_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("Group", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="group_memberships")
    added_by = relationship("User", foreign_keys=[added_by_id])

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_user"),
        Index("ix_group_members_composite", "group_id", "user_id"),
    )
