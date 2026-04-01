"""SocialAccount model for OAuth linking."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.database import Base


class SocialAccount(Base):
    """OAuth social account linking table."""
    __tablename__ = "social_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False, index=True)
    provider_user_id = Column(String(255), nullable=False, index=True)
    provider_email = Column(String(255), nullable=False)
    access_token = Column(String(500), nullable=True)
    refresh_token = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    profile_data = Column(JSON, default=dict)
    linked_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="social_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_social_provider_user"),
        Index("ix_social_accounts_user_id", "user_id"),
    )
