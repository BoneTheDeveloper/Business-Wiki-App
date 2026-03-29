"""Group management service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import uuid as uuid_module

from app.models.models import Group, GroupMember, Organization, User


class GroupService:
    """Service for group management operations."""

    @staticmethod
    async def create_group(
        db: AsyncSession,
        org_id: UUID,
        name: str,
        description: Optional[str] = None,
        created_by_id: Optional[UUID] = None
    ) -> Group:
        """Create a new group in organization."""
        # Check name uniqueness in org
        existing = await db.execute(
            select(Group).where(
                Group.organization_id == org_id,
                Group.name == name
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Group '{name}' already exists in this organization")

        group = Group(
            id=uuid_module.uuid4(),
            organization_id=org_id,
            name=name,
            description=description,
            created_by_id=created_by_id,
            created_at=datetime.utcnow()
        )
        db.add(group)
        await db.flush()
        return group

    @staticmethod
    async def get_group(
        db: AsyncSession,
        group_id: UUID,
        with_members: bool = False
    ) -> Optional[Group]:
        """Get group by ID."""
        query = select(Group).where(Group.id == group_id)

        if with_members:
            query = query.options(selectinload(Group.members))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_organization_groups(
        db: AsyncSession,
        org_id: UUID
    ) -> List[Group]:
        """List all groups in organization."""
        result = await db.execute(
            select(Group)
            .where(Group.organization_id == org_id)
            .order_by(Group.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_group(
        db: AsyncSession,
        group_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Group]:
        """Update group details."""
        group = await GroupService.get_group(db, group_id)

        if not group:
            return None

        if name:
            # Check name uniqueness
            existing = await db.execute(
                select(Group).where(
                    Group.organization_id == group.organization_id,
                    Group.name == name,
                    Group.id != group_id
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Group '{name}' already exists")

            group.name = name

        if description is not None:
            group.description = description

        await db.flush()
        return group

    @staticmethod
    async def delete_group(
        db: AsyncSession,
        group_id: UUID
    ) -> bool:
        """Delete a group."""
        group = await GroupService.get_group(db, group_id)

        if not group:
            return False

        await db.delete(group)
        await db.flush()
        return True

    @staticmethod
    async def add_member(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        added_by_id: Optional[UUID] = None
    ) -> GroupMember:
        """Add user to group."""
        # Check if already a member
        existing = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("User is already a member of this group")

        member = GroupMember(
            id=uuid_module.uuid4(),
            group_id=group_id,
            user_id=user_id,
            added_by_id=added_by_id,
            added_at=datetime.utcnow()
        )
        db.add(member)
        await db.flush()
        return member

    @staticmethod
    async def remove_member(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID
    ) -> bool:
        """Remove user from group."""
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            return False

        await db.delete(member)
        await db.flush()
        return True

    @staticmethod
    async def get_group_members(
        db: AsyncSession,
        group_id: UUID
    ) -> List[GroupMember]:
        """Get all members of a group."""
        result = await db.execute(
            select(GroupMember)
            .where(GroupMember.group_id == group_id)
            .options(selectinload(GroupMember.user))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_member_count(
        db: AsyncSession,
        group_id: UUID
    ) -> int:
        """Get number of members in group."""
        result = await db.execute(
            select(func.count(GroupMember.id)).where(
                GroupMember.group_id == group_id
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def is_member(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID
    ) -> bool:
        """Check if user is a member of group."""
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_user_groups(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID
    ) -> List[Group]:
        """Get all groups user is a member of in organization."""
        result = await db.execute(
            select(Group)
            .join(GroupMember)
            .where(
                Group.organization_id == org_id,
                GroupMember.user_id == user_id
            )
            .order_by(Group.name)
        )
        return list(result.scalars().all())


group_service = GroupService()
