"""SQLAlchemy ORM models."""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, Enum as SQLEnum, Index, UniqueConstraint, CheckConstraint, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid
import enum
from datetime import datetime
from app.models.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration."""
    USER = "user"
    EDITOR = "editor"
    ADMIN = "admin"


class DocumentStatus(str, enum.Enum):
    """Document processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OrgRole(str, enum.Enum):
    """Organization member role enumeration."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class DocumentVisibility(str, enum.Enum):
    """Document visibility enumeration."""
    PUBLIC = "public"       # All org members can view
    RESTRICTED = "restricted"  # Group/user-based access
    PRIVATE = "private"     # Owner + admins only


class AccessLevel(str, enum.Enum):
    """Document access level enumeration."""
    VIEW = "view"
    EDIT = "edit"


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Changed to nullable for OAuth-only users
    email_verified = Column(Boolean, nullable=True)  # Email verification status from OAuth
    oauth_provider = Column(String(50), nullable=True, index=True)  # OAuth provider name
    oauth_id = Column(String(255), nullable=True)  # OAuth provider user ID
    name = Column(String(255), nullable=True)  # User display name from OAuth
    avatar_url = Column(String(500), nullable=True)  # User avatar URL from OAuth
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="user")
    social_accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")
    owned_organizations = relationship("Organization", foreign_keys="Organization.owner_id", back_populates="owner")
    organization_memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")
    group_memberships = relationship("GroupMember", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_users_oauth_provider_oauth_id', 'oauth_provider', 'oauth_id'),
    )


class Document(Base):
    """Document model for uploaded files."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    format = Column(String(20))
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING)
    visibility = Column(SQLEnum(DocumentVisibility), default=DocumentVisibility.PRIVATE)
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
        Index('ix_documents_org_visibility', 'organization_id', 'visibility'),
    )


class DocumentChunk(Base):
    """Document chunk model with vector embedding."""
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-small dimensions
    chunk_index = Column(Integer, nullable=False)
    chunk_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")


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
        UniqueConstraint('provider', 'provider_user_id', name='uq_social_provider_user'),
        Index('ix_social_accounts_user_id', 'user_id'),
    )


# Multi-Tenancy Models

class Organization(Base):
    """Organization model for multi-tenancy."""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    # Quotas
    max_documents = Column(Integer, default=100)
    max_storage_bytes = Column(BigInteger, default=5368709120)  # 5GB

    # Usage (denormalized for performance)
    current_documents = Column(Integer, default=0)
    current_storage_bytes = Column(BigInteger, default=0)

    # Settings
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_organizations")
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="organization", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="organization")
    invitations = relationship("Invitation", back_populates="organization", cascade="all, delete-orphan")


class OrganizationMember(Base):
    """Organization membership with roles."""
    __tablename__ = "organization_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(SQLEnum(OrgRole), nullable=False, default=OrgRole.MEMBER)

    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="organization_memberships")
    invited_by = relationship("User", foreign_keys=[invited_by_id])

    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='uq_org_user'),
        Index('ix_org_members_composite', 'organization_id', 'user_id'),
    )


class Group(Base):
    """Document access groups."""
    __tablename__ = "groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    created_by = relationship("User")
    document_access = relationship("DocumentAccess", back_populates="group")

    __table_args__ = (
        UniqueConstraint('organization_id', 'name', name='uq_org_group_name'),
    )


class GroupMember(Base):
    """Group membership."""
    __tablename__ = "group_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    added_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    group = relationship("Group", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="group_memberships")
    added_by = relationship("User", foreign_keys=[added_by_id])

    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uq_group_user'),
        Index('ix_group_members_composite', 'group_id', 'user_id'),
    )


class DocumentAccess(Base):
    """Document access permissions."""
    __tablename__ = "document_access"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Access grantee (one must be set)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True)

    access_level = Column(SQLEnum(AccessLevel), nullable=False, default=AccessLevel.VIEW)

    granted_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="access_list")
    user = relationship("User", foreign_keys=[user_id])
    group = relationship("Group", back_populates="document_access")
    granted_by = relationship("User", foreign_keys=[granted_by_id])

    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL AND group_id IS NULL) OR '
            '(user_id IS NULL AND group_id IS NOT NULL)',
            name='ck_access_target'
        ),
        Index('ix_doc_access_composite', 'document_id', 'user_id', 'group_id'),
    )


class Invitation(Base):
    """Email invitations to organizations."""
    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    invitee_email = Column(String(255), nullable=False, index=True)
    role = Column(SQLEnum(OrgRole), nullable=False, default=OrgRole.MEMBER)

    # Security
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    token_salt = Column(String(64), nullable=False)

    # Tracking
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    used = Column(Boolean, default=False)

    # Relationships
    organization = relationship("Organization", back_populates="invitations")
    invited_by = relationship("User")
