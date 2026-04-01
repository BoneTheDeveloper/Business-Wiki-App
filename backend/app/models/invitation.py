"""Invitation model for email invitations to organizations."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.database import Base
from app.models.enums import OrgRole


class Invitation(Base):
    """Email invitations to organizations."""
    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    invitee_email = Column(String(255), nullable=False, index=True)
    # DB uses VARCHAR(20) with CHECK constraint, not PG native enum
    role = Column(String(20), default=OrgRole.MEMBER.value, nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    token_salt = Column(String(64), nullable=False)
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    used = Column(Boolean, default=False)

    organization = relationship("Organization", back_populates="invitations")
    invited_by = relationship("User")
