"""Document-related Pydantic schemas."""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models.enums import DocumentStatus, DocumentVisibility, AccessLevel


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
