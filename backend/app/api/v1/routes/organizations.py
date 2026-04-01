"""Organization management API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.models.database import get_db
from app.models.models import User, OrgRole
from app.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationWithMemberCount, OrganizationMemberCreate,
    OrganizationMemberUpdate, OrganizationMemberResponse,
)
from app.schemas.quota import QuotaUsage
from app.dependencies import get_current_user
from app.services.organization_service import organization_service
from app.services.permission_service import permission_service, Permission

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new organization."""
    try:
        org = await organization_service.create_organization(
            db=db,
            name=data.name,
            owner_id=current_user.id,
            slug=data.slug
        )
        await db.commit()
        await db.refresh(org)
        return org
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[OrganizationResponse])
async def list_my_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all organizations the current user is a member of."""
    orgs = await organization_service.list_user_organizations(db, current_user.id)

    # Add member count for each org
    result = []
    for org in orgs:
        member_count = await organization_service.get_member_count(db, org.id)
        org_dict = OrganizationResponse.model_validate(org).model_dump()
        result.append(OrganizationWithMemberCount(**org_dict, member_count=member_count))

    return result


@router.get("/default", response_model=OrganizationResponse)
async def get_or_create_default_organization(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's default organization or create one if none exists."""
    try:
        org = await organization_service.get_or_create_user_organization(db, current_user)
        await db.commit()
        await db.refresh(org)
        return org
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{org_id}", response_model=OrganizationWithMemberCount)
async def get_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get organization by ID."""
    # Check membership
    if not await organization_service.is_member(db, org_id, current_user.id):
        raise HTTPException(status_code=404, detail="Organization not found")

    org = await organization_service.get_organization(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    member_count = await organization_service.get_member_count(db, org_id)
    org_dict = OrganizationResponse.model_validate(org).model_dump()
    return OrganizationWithMemberCount(**org_dict, member_count=member_count)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: UUID,
    data: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update organization settings (owner/admin only)."""
    # Check permission
    if not await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.MANAGE
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        org = await organization_service.update_organization(
            db=db,
            org_id=org_id,
            name=data.name,
            settings=data.settings
        )
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        await db.commit()
        await db.refresh(org)
        return org
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{org_id}/quota", response_model=QuotaUsage)
async def get_organization_quota(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get organization quota usage."""
    if not await organization_service.is_member(db, org_id, current_user.id):
        raise HTTPException(status_code=404, detail="Organization not found")

    org = await organization_service.get_organization(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return QuotaUsage(
        documents_used=org.current_documents,
        documents_limit=org.max_documents,
        storage_used_bytes=org.current_storage_bytes,
        storage_limit_bytes=org.max_storage_bytes,
        documents_percentage=(org.current_documents / org.max_documents * 100) if org.max_documents > 0 else 0,
        storage_percentage=(org.current_storage_bytes / org.max_storage_bytes * 100) if org.max_storage_bytes > 0 else 0
    )


# Member endpoints

@router.get("/{org_id}/members", response_model=list[OrganizationMemberResponse])
async def list_organization_members(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all members of organization."""
    if not await organization_service.is_member(db, org_id, current_user.id):
        raise HTTPException(status_code=404, detail="Organization not found")

    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.models.models import OrganizationMember

    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org_id)
        .options(selectinload(OrganizationMember.user))
        .order_by(OrganizationMember.joined_at)
    )
    members = result.scalars().all()

    return [
        OrganizationMemberResponse(
            id=m.id,
            organization_id=m.organization_id,
            user_id=m.user_id,
            role=m.role,
            joined_at=m.joined_at,
            user=m.user
        )
        for m in members
    ]


@router.post("/{org_id}/members", response_model=OrganizationMemberResponse, status_code=201)
async def add_organization_member(
    org_id: UUID,
    data: OrganizationMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add member directly to organization (admin+ only)."""
    if not await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.INVITE
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Cannot add as owner
    if data.role == OrgRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot add members as owner")

    try:
        member = await organization_service.add_member(
            db=db,
            org_id=org_id,
            user_id=data.user_id,
            role=data.role,
            invited_by_id=current_user.id
        )
        await db.commit()

        # Fetch with user data
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        from app.models.models import OrganizationMember

        result = await db.execute(
            select(OrganizationMember)
            .where(OrganizationMember.id == member.id)
            .options(selectinload(OrganizationMember.user))
        )
        member = result.scalar_one()

        return OrganizationMemberResponse(
            id=member.id,
            organization_id=member.organization_id,
            user_id=member.user_id,
            role=member.role,
            joined_at=member.joined_at,
            user=member.user
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{org_id}/members/{user_id}", response_model=OrganizationMemberResponse)
async def update_member_role(
    org_id: UUID,
    user_id: UUID,
    data: OrganizationMemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update member's role (admin+ only, cannot change to/from owner)."""
    if not await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.INVITE
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Cannot set to owner
    if data.role == OrgRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot change role to owner")

    # Check if can manage this member
    if not await permission_service.can_manage_member(
        db, org_id, current_user.id, user_id, data.role
    ):
        raise HTTPException(status_code=403, detail="Cannot manage this member")

    try:
        member = await organization_service.update_member_role(
            db=db,
            org_id=org_id,
            user_id=user_id,
            new_role=data.role
        )
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        await db.commit()

        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        from app.models.models import OrganizationMember

        result = await db.execute(
            select(OrganizationMember)
            .where(OrganizationMember.id == member.id)
            .options(selectinload(OrganizationMember.user))
        )
        member = result.scalar_one()

        return OrganizationMemberResponse(
            id=member.id,
            organization_id=member.organization_id,
            user_id=member.user_id,
            role=member.role,
            joined_at=member.joined_at,
            user=member.user
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{org_id}/members/{user_id}")
async def remove_organization_member(
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove member from organization (admin+ only)."""
    if not await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.INVITE
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Users can remove themselves
    if user_id != current_user.id:
        if not await permission_service.can_manage_member(
            db, org_id, current_user.id, user_id
        ):
            raise HTTPException(status_code=403, detail="Cannot remove this member")

    try:
        removed = await organization_service.remove_member(
            db=db,
            org_id=org_id,
            user_id=user_id
        )
        if not removed:
            raise HTTPException(status_code=404, detail="Member not found")

        await db.commit()
        return {"message": "Member removed successfully"}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
