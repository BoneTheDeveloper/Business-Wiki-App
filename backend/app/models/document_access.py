"""DocumentAccess model for document permission control."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.database import Base
from app.models.enums import AccessLevel


class DocumentAccess(Base):
    """Document access permissions."""
    __tablename__ = "document_access"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    group_id = Column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    # DB uses VARCHAR(10) with CHECK constraint, not PG native enum
    access_level = Column(String(10), default=AccessLevel.VIEW.value, nullable=False)
    granted_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="access_list")
    user = relationship("User", foreign_keys=[user_id])
    group = relationship("Group", back_populates="document_access")
    granted_by = relationship("User", foreign_keys=[granted_by_id])

    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND group_id IS NULL) OR "
            "(user_id IS NULL AND group_id IS NOT NULL)",
            name="ck_access_target",
        ),
        Index("ix_doc_access_composite", "document_id", "user_id", "group_id"),
    )
