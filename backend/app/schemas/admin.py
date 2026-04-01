"""Admin Pydantic schemas."""
from pydantic import BaseModel
from typing import List
from app.schemas.user import UserResponse


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
