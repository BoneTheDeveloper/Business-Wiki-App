"""Group management API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.database import get_db
from app.models.models import User
from app.schemas.group import (
    GroupCreate, GroupUpdate, GroupResponse, GroupWithMemberCount,
    GroupMemberAdd, GroupMemberResponse,
)
from app.dependencies import get_current_user
from app.services.group_service import group_service
from app.services.organization_service import organization_service
from app.services.permission_service import permission_service, Permission

router = APIRouter(prefix="/organizations/{org_id}/groups", tags=["groups"])


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    org_id: UUID,
    data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new group in organization."""
    # Check permission
    if not await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.CREATE_GROUP
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions to create groups")

    try:
        group = await group_service.create_group(
            db=db,
            org_id=org_id,
            name=data.name,
            description=data.description,
            created_by_id=current_user.id
        )
        await db.commit()
        await db.refresh(group)
        return group
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[GroupWithMemberCount])
async def list_organization_groups(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all groups in organization."""
    if not await organization_service.is_member(db, org_id, current_user.id):
        raise HTTPException(status_code=404, detail="Organization not found")

    groups = await group_service.list_organization_groups(db, org_id)

    result = []
    for group in groups:
        member_count = await group_service.get_member_count(db, group.id)
        group_dict = GroupResponse.model_validate(group).model_dump()
        result.append(GroupWithMemberCount(**group_dict, member_count=member_count))

    return result


@router.get("/{group_id}", response_model=GroupWithMemberCount)
async def get_group(
    org_id: UUID,
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get group details."""
    if not await organization_service.is_member(db, org_id, current_user.id):
        raise HTTPException(status_code=404, detail="Organization not found")

    group = await group_service.get_group(db, group_id)

    if not group or group.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Group not found")

    member_count = await group_service.get_member_count(db, group_id)
    group_dict = GroupResponse.model_validate(group).model_dump()
    return GroupWithMemberCount(**group_dict, member_count=member_count)


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    org_id: UUID,
    group_id: UUID,
    data: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update group details (admin+ or group creator)."""
    group = await group_service.get_group(db, group_id)

    if not group or group.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Group not found")

    # Check if user can manage this group
    is_admin = await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.MANAGE
    )
    is_creator = group.created_by_id == current_user.id

    if not is_admin and not is_creator:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        updated_group = await group_service.update_group(
            db=db,
            group_id=group_id,
            name=data.name,
            description=data.description
        )
        await db.commit()
        await db.refresh(updated_group)
        return updated_group
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{group_id}")
async def delete_group(
    org_id: UUID,
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a group (admin+ or group creator)."""
    group = await group_service.get_group(db, group_id)

    if not group or group.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Group not found")

    # Check if user can manage this group
    is_admin = await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.MANAGE
    )
    is_creator = group.created_by_id == current_user.id

    if not is_admin and not is_creator:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        deleted = await group_service.delete_group(db=db, group_id=group_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Group not found")

        await db.commit()
        return {"message": "Group deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# Group member endpoints

@router.get("/{group_id}/members", response_model=list[GroupMemberResponse])
async def list_group_members(
    org_id: UUID,
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all members of a group."""
    if not await organization_service.is_member(db, org_id, current_user.id):
        raise HTTPException(status_code=404, detail="Organization not found")

    group = await group_service.get_group(db, group_id)

    if not group or group.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Group not found")

    members = await group_service.get_group_members(db, group_id)

    return [
        GroupMemberResponse(
            id=m.id,
            group_id=m.group_id,
            user_id=m.user_id,
            added_at=m.added_at,
            user=m.user
        )
        for m in members
    ]


@router.post("/{group_id}/members", response_model=GroupMemberResponse, status_code=201)
async def add_group_member(
    org_id: UUID,
    group_id: UUID,
    data: GroupMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add member to group (must be org member first)."""
    # Check if target user is org member
    if not await organization_service.is_member(db, org_id, data.user_id):
        raise HTTPException(status_code=400, detail="User must be organization member first")

    group = await group_service.get_group(db, group_id)

    if not group or group.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Group not found")

    # Check if current user can add to this group
    is_admin = await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.MANAGE
    )
    is_creator = group.created_by_id == current_user.id

    if not is_admin and not is_creator:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        member = await group_service.add_member(
            db=db,
            group_id=group_id,
            user_id=data.user_id,
            added_by_id=current_user.id
        )
        await db.commit()

        # Fetch with user data
        members = await group_service.get_group_members(db, group_id)
        for m in members:
            if m.id == member.id:
                return GroupMemberResponse(
                    id=m.id,
                    group_id=m.group_id,
                    user_id=m.user_id,
                    added_at=m.added_at,
                    user=m.user
                )

        raise HTTPException(status_code=500, detail="Failed to fetch member")
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{group_id}/members/{user_id}")
async def remove_group_member(
    org_id: UUID,
    group_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove member from group."""
    group = await group_service.get_group(db, group_id)

    if not group or group.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Group not found")

    # Users can remove themselves, or admins/creators can remove others
    is_self = user_id == current_user.id
    is_admin = await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.MANAGE
    )
    is_creator = group.created_by_id == current_user.id

    if not is_self and not is_admin and not is_creator:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        removed = await group_service.remove_member(
            db=db,
            group_id=group_id,
            user_id=user_id
        )
        if not removed:
            raise HTTPException(status_code=404, detail="Member not found in group")

        await db.commit()
        return {"message": "Member removed from group"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}", response_model=list[GroupResponse])
async def get_user_groups_in_org(
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all groups a user is a member of in this organization."""
    if not await organization_service.is_member(db, org_id, current_user.id):
        raise HTTPException(status_code=404, detail="Organization not found")

    # Users can only view their own groups, or admins can view anyone's
    is_self = user_id == current_user.id
    is_admin = await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.MANAGE
    )

    if not is_self and not is_admin:
        raise HTTPException(status_code=403, detail="Can only view your own groups")

    groups = await group_service.get_user_groups(db, org_id, user_id)
    return groups
