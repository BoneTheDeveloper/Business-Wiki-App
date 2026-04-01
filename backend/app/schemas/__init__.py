"""Pydantic schemas package."""
from app.schemas.auth import SupabaseUserPayload
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.document import (
    DocumentResponse, DocumentList,
    DocumentAccessGrant, DocumentAccessResponse, DocumentVisibilityUpdate,
)
from app.schemas.search import (
    SearchRequest, SearchResponse, SearchResult,
    ChatRequest, ChatResponse, ChatMessage, ChatSource,
)
from app.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse, OrganizationWithMemberCount,
    OrganizationMemberCreate, OrganizationMemberUpdate, OrganizationMemberResponse,
    InvitationCreate, InvitationResponse, InvitationAccept, InvitationList,
)
from app.schemas.group import (
    GroupCreate, GroupUpdate, GroupResponse, GroupWithMemberCount,
    GroupMemberAdd, GroupMemberResponse,
)
from app.schemas.admin import UserListResponse, StatsResponse
from app.schemas.quota import QuotaUsage

__all__ = [
    # Auth
    "SupabaseUserPayload",
    # User
    "UserResponse", "UserUpdate",
    # Document
    "DocumentResponse", "DocumentList",
    "DocumentAccessGrant", "DocumentAccessResponse", "DocumentVisibilityUpdate",
    # Search & Chat
    "SearchRequest", "SearchResponse", "SearchResult",
    "ChatRequest", "ChatResponse", "ChatMessage", "ChatSource",
    # Organization
    "OrganizationCreate", "OrganizationUpdate", "OrganizationResponse", "OrganizationWithMemberCount",
    "OrganizationMemberCreate", "OrganizationMemberUpdate", "OrganizationMemberResponse",
    "InvitationCreate", "InvitationResponse", "InvitationAccept", "InvitationList",
    # Group
    "GroupCreate", "GroupUpdate", "GroupResponse", "GroupWithMemberCount",
    "GroupMemberAdd", "GroupMemberResponse",
    # Admin
    "UserListResponse", "StatsResponse",
    # Quota
    "QuotaUsage",
]
