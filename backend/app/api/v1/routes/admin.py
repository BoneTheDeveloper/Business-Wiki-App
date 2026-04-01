"""Admin API routes for user management and system stats."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.models.database import get_db
from app.models.models import User, UserRole, Document, DocumentStatus, DocumentChunk
from app.schemas.user import UserResponse
from app.dependencies import get_current_user, require_role

router = APIRouter(prefix="/admin", tags=["admin"])


class UserUpdate(BaseModel):
    """User update request."""
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserListResponse(BaseModel):
    """Paginated user list."""
    items: List[UserResponse]
    total: int


class StatsResponse(BaseModel):
    """System statistics."""
    total_documents: int
    total_users: int
    active_users: int
    total_chunks: int
    queries_today: int
    documents_by_status: dict
    documents_by_format: dict


class ActivityItem(BaseModel):
    """Activity log item."""
    type: str
    user_email: str
    description: str
    timestamp: datetime


@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """List all users with optional filters (admin only)."""
    query = select(User)

    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    # Count total
    count_query = select(func.count(User.id))
    if role:
        count_query = count_query.where(User.role == role)
    if is_active is not None:
        count_query = count_query.where(User.is_active == is_active)
    total = (await db.execute(count_query)).scalar() or 0

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Update user role or status (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    # Prevent self-demotion
    if user.id == current_user.id and data.role and data.role != UserRole.ADMIN:
        raise HTTPException(400, "Cannot demote yourself")

    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Get system statistics (admin only)."""
    # Document count
    doc_count = (await db.execute(select(func.count(Document.id)))).scalar() or 0

    # Chunk count
    chunk_count = (await db.execute(select(func.count(DocumentChunk.id)))).scalar() or 0

    # User counts
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_count = (await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )).scalar() or 0

    # Documents by status
    status_result = await db.execute(
        select(Document.status, func.count(Document.id)).group_by(Document.status)
    )
    by_status = {row[0].value: row[1] for row in status_result}

    # Documents by format
    format_result = await db.execute(
        select(Document.format, func.count(Document.id)).group_by(Document.format)
    )
    by_format = {row[0] or "unknown": row[1] for row in format_result}

    return StatsResponse(
        total_documents=doc_count,
        total_users=user_count,
        active_users=active_count,
        total_chunks=chunk_count,
        queries_today=0,  # TODO: Add query logging
        documents_by_status=by_status,
        documents_by_format=by_format
    )


@router.get("/activity", response_model=List[ActivityItem])
async def get_activity(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Get recent activity (admin only)."""
    # Get recent documents
    result = await db.execute(
        select(Document, User)
        .join(User, Document.user_id == User.id)
        .order_by(Document.created_at.desc())
        .limit(limit)
    )
    rows = result.all()

    activities = []
    for doc, user in rows:
        activities.append(ActivityItem(
            type="document_upload",
            user_email=user.email,
            description=f"Uploaded {doc.filename}",
            timestamp=doc.created_at
        ))

    return activities
