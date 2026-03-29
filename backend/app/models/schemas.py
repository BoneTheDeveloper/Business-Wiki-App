"""Pydantic schemas for API validation and serialization."""
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID
from app.models.models import UserRole, DocumentStatus, OrgRole, DocumentVisibility, AccessLevel


# Auth schemas
class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token refresh request."""
    refresh_token: str


# User schemas
class UserResponse(BaseModel):
    """User response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    is_active: bool
    email_verified: Optional[bool] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    oauth_provider: Optional[str] = None
    created_at: datetime


class UserUpdate(BaseModel):
    """User update request (admin)."""
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


# Document schemas
class DocumentResponse(BaseModel):
    """Document response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    file_size: Optional[int]
    format: Optional[str]
    status: DocumentStatus
    visibility: Optional[DocumentVisibility] = DocumentVisibility.PRIVATE
    organization_id: Optional[UUID] = None
    metadata: dict = Field(default=dict, alias="doc_metadata")
    created_at: datetime


class DocumentList(BaseModel):
    """Paginated document list response."""
    items: List[DocumentResponse]
    total: int
    skip: int
    limit: int


# Search schemas
class SearchRequest(BaseModel):
    """Semantic search request."""
    query: str
    top_k: int = 10
    document_ids: Optional[List[str]] = None
    filters: Optional[dict] = None


class SearchResult(BaseModel):
    """Single search result."""
    chunk_id: str
    content: str
    metadata: dict
    document_id: str
    filename: str
    format: str
    similarity: float


class SearchResponse(BaseModel):
    """Search response with results."""
    query: str
    results: List[SearchResult]
    total: int


# Chat schemas
class ChatMessage(BaseModel):
    """Chat message in conversation."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Chat request with optional context."""
    query: str
    document_ids: Optional[List[str]] = None
    conversation_history: Optional[List[ChatMessage]] = None
    top_k: int = 5


class ChatSource(BaseModel):
    """Source citation in chat response."""
    document_id: str
    filename: str
    chunk_id: str
    similarity: float
    page: Optional[int] = None


class ChatResponse(BaseModel):
    """Chat response with sources."""
    answer: str
    sources: List[ChatSource]
    model: str
    usage: dict


# Admin schemas
class UserListResponse(BaseModel):
    """Paginated user list response."""
    items: List[UserResponse]
    total: int


class StatsResponse(BaseModel):
    """System statistics response."""
    total_documents: int
    total_users: int
    total_chunks: int
    queries_today: int
    documents_by_status: dict
    documents_by_format: dict


# Multi-Tenancy Schemas

# Organization schemas
class OrganizationCreate(BaseModel):
    """Organization creation request."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=3, max_length=100, pattern=r"^[a-z0-9-]+$")


class OrganizationUpdate(BaseModel):
    """Organization update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    settings: Optional[dict] = None


class OrganizationResponse(BaseModel):
    """Organization response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    owner_id: UUID
    max_documents: int
    max_storage_bytes: int
    current_documents: int
    current_storage_bytes: int
    settings: dict
    is_active: bool
    created_at: datetime


class OrganizationWithMemberCount(OrganizationResponse):
    """Organization response with member count."""
    member_count: int = 0


# Organization Member schemas
class OrganizationMemberCreate(BaseModel):
    """Add member to organization (direct, not via invitation)."""
    user_id: UUID
    role: OrgRole = OrgRole.MEMBER


class OrganizationMemberUpdate(BaseModel):
    """Update member role."""
    role: OrgRole


class OrganizationMemberResponse(BaseModel):
    """Organization member response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    user_id: UUID
    role: OrgRole
    joined_at: datetime
    user: Optional[UserResponse] = None


# Invitation schemas
class InvitationCreate(BaseModel):
    """Create invitation request."""
    invitee_email: EmailStr
    role: OrgRole = OrgRole.MEMBER


class InvitationResponse(BaseModel):
    """Invitation response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    invitee_email: str
    role: OrgRole
    created_at: datetime
    expires_at: datetime
    used: bool


class InvitationAccept(BaseModel):
    """Accept invitation request."""
    token: str


class InvitationList(BaseModel):
    """Paginated invitation list response."""
    items: List[InvitationResponse]
    total: int


# Group schemas
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


# Group Member schemas
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


# Document Access schemas
class DocumentAccessGrant(BaseModel):
    """Grant document access request."""
    user_id: Optional[UUID] = None
    group_id: Optional[UUID] = None
    access_level: AccessLevel = AccessLevel.VIEW


class DocumentAccessResponse(BaseModel):
    """Document access response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    user_id: Optional[UUID]
    group_id: Optional[UUID]
    access_level: AccessLevel
    granted_at: datetime


class DocumentVisibilityUpdate(BaseModel):
    """Update document visibility."""
    visibility: DocumentVisibility


# Quota schemas
class QuotaUsage(BaseModel):
    """Organization quota usage."""
    documents_used: int
    documents_limit: int
    storage_used_bytes: int
    storage_limit_bytes: int
    documents_percentage: float
    storage_percentage: float
