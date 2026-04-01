"""Document and DocumentChunk models."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.models.database import Base
from app.models.enums import DocumentStatus, DocumentVisibility


class Document(Base):
    """Document model for uploaded files."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    format = Column(String(20))
    # DB uses VARCHAR(20) with CHECK constraints, not PG native enum
    status = Column(String(20), default=DocumentStatus.PENDING.value, nullable=False)
    visibility = Column(String(20), default=DocumentVisibility.PRIVATE.value, nullable=False)
    doc_metadata = Column(JSON, default=dict)
    extracted_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="documents")
    organization = relationship("Organization", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    access_list = relationship("DocumentAccess", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_documents_org_visibility", "organization_id", "visibility"),
    )


class DocumentChunk(Base):
    """Document chunk model with vector embedding."""
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-small dimensions
    chunk_index = Column(Integer, nullable=False)
    chunk_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")
