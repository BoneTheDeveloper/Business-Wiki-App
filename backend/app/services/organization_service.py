"""Organization management service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import re
import uuid as uuid_module

from app.models.models import (
    Organization, OrganizationMember, User, Document,
    OrgRole, DocumentVisibility
)


class OrganizationService:
    """Service for organization management operations."""

    @staticmethod
    def generate_slug(name: str) -> str:
        """Generate URL-friendly slug from organization name."""
        # Convert to lowercase
        slug = name.lower().strip()
        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        # Limit length
        return slug[:100]

    @staticmethod
    async def ensure_unique_slug(db: AsyncSession, base_slug: str, exclude_id: Optional[UUID] = None) -> str:
        """Ensure slug is unique by adding suffix if needed."""
        slug = base_slug
        counter = 1

        while True:
            query = select(Organization).where(Organization.slug == slug)
            if exclude_id:
                query = query.where(Organization.id != exclude_id)

            result = await db.execute(query)
            if not result.scalar_one_or_none():
                return slug

            slug = f"{base_slug}-{counter}"
            counter += 1

    @staticmethod
    async def create_organization(
        db: AsyncSession,
        name: str,
        owner_id: UUID,
        slug: Optional[str] = None,
        max_documents: int = 100,
        max_storage_bytes: int = 5368709120  # 5GB
    ) -> Organization:
        """Create a new organization with owner as member."""
        # Generate slug if not provided
        if not slug:
            slug = OrganizationService.generate_slug(name)

        # Ensure uniqueness
        slug = await OrganizationService.ensure_unique_slug(db, slug)

        # Create organization
        org = Organization(
            id=uuid_module.uuid4(),
            name=name,
            slug=slug,
            owner_id=owner_id,
            max_documents=max_documents,
            max_storage_bytes=max_storage_bytes,
            current_documents=0,
            current_storage_bytes=0,
            settings={},
            is_active=True
        )
        db.add(org)
        await db.flush()

        # Add owner as member with owner role
        member = OrganizationMember(
            id=uuid_module.uuid4(),
            organization_id=org.id,
            user_id=owner_id,
            role=OrgRole.OWNER,
            invited_by_id=None,
            joined_at=datetime.utcnow()
        )
        db.add(member)
        await db.flush()

        return org

    @staticmethod
    async def get_organization(
        db: AsyncSession,
        org_id: UUID,
        with_members: bool = False
    ) -> Optional[Organization]:
        """Get organization by ID."""
        query = select(Organization).where(Organization.id == org_id)
        if with_members:
            query = query.options(selectinload(Organization.members))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_organization_by_slug(db: AsyncSession, slug: str) -> Optional[Organization]:
        """Get organization by slug."""
        result = await db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_user_organizations(
        db: AsyncSession,
        user_id: UUID
    ) -> List[Organization]:
        """List all organizations user is a member of."""
        result = await db.execute(
            select(Organization)
            .join(OrganizationMember)
            .where(OrganizationMember.user_id == user_id)
            .where(Organization.is_active == True)
            .order_by(Organization.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_organization(
        db: AsyncSession,
        org_id: UUID,
        name: Optional[str] = None,
        settings: Optional[dict] = None
    ) -> Optional[Organization]:
        """Update organization details."""
        org = await OrganizationService.get_organization(db, org_id)
        if not org:
            return None

        if name:
            org.name = name
        if settings is not None:
            org.settings = settings

        org.updated_at = datetime.utcnow()
        await db.flush()
        return org

    @staticmethod
    async def get_or_create_user_organization(
        db: AsyncSession,
        user: User
    ) -> Organization:
        """Get user's first organization or create default one."""
        # Check if user has any organization
        orgs = await OrganizationService.list_user_organizations(db, user.id)

        if orgs:
            return orgs[0]

        # Create default organization
        default_name = f"{user.email}'s Workspace"
        return await OrganizationService.create_organization(
            db=db,
            name=default_name,
            owner_id=user.id
        )

    @staticmethod
    async def add_member(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID,
        role: OrgRole,
        invited_by_id: Optional[UUID] = None
    ) -> OrganizationMember:
        """Add a member to organization."""
        # Check if already a member
        existing = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("User is already a member of this organization")

        member = OrganizationMember(
            id=uuid_module.uuid4(),
            organization_id=org_id,
            user_id=user_id,
            role=role,
            invited_by_id=invited_by_id,
            joined_at=datetime.utcnow()
        )
        db.add(member)
        await db.flush()
        return member

    @staticmethod
    async def update_member_role(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID,
        new_role: OrgRole
    ) -> Optional[OrganizationMember]:
        """Update member's role."""
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            return None

        # Prevent removing the last owner
        if member.role == OrgRole.OWNER and new_role != OrgRole.OWNER:
            owner_count = await db.execute(
                select(func.count(OrganizationMember.id)).where(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.role == OrgRole.OWNER
                )
            )
            if (owner_count.scalar() or 0) <= 1:
                raise ValueError("Cannot remove the last owner")

        member.role = new_role
        await db.flush()
        return member

    @staticmethod
    async def remove_member(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID
    ) -> bool:
        """Remove member from organization."""
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            return False

        # Prevent removing the last owner
        if member.role == OrgRole.OWNER:
            owner_count = await db.execute(
                select(func.count(OrganizationMember.id)).where(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.role == OrgRole.OWNER
                )
            )
            if (owner_count.scalar() or 0) <= 1:
                raise ValueError("Cannot remove the last owner")

        await db.delete(member)
        await db.flush()
        return True

    @staticmethod
    async def get_member_count(db: AsyncSession, org_id: UUID) -> int:
        """Get number of members in organization."""
        result = await db.execute(
            select(func.count(OrganizationMember.id)).where(
                OrganizationMember.organization_id == org_id
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def is_member(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID
    ) -> bool:
        """Check if user is a member of organization."""
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_member_role(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID
    ) -> Optional[OrgRole]:
        """Get user's role in organization."""
        result = await db.execute(
            select(OrganizationMember.role).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_usage_stats(
        db: AsyncSession,
        org_id: UUID,
        document_delta: int = 0,
        storage_delta: int = 0
    ) -> None:
        """Update organization usage statistics."""
        await db.execute(
            update(Organization)
            .where(Organization.id == org_id)
            .values(
                current_documents=Organization.current_documents + document_delta,
                current_storage_bytes=Organization.current_storage_bytes + storage_delta,
                updated_at=datetime.utcnow()
            )
        )

    @staticmethod
    async def check_quota(
        db: AsyncSession,
        org_id: UUID,
        additional_documents: int = 0,
        additional_storage: int = 0
    ) -> dict:
        """Check if organization has quota for additional resources."""
        org = await OrganizationService.get_organization(db, org_id)
        if not org:
            return {"allowed": False, "reason": "Organization not found"}

        new_doc_count = org.current_documents + additional_documents
        new_storage = org.current_storage_bytes + additional_storage

        if new_doc_count > org.max_documents:
            return {
                "allowed": False,
                "reason": f"Document limit reached ({org.max_documents})"
            }

        if new_storage > org.max_storage_bytes:
            return {
                "allowed": False,
                "reason": f"Storage limit reached ({org.max_storage_bytes / (1024**3):.1f}GB)"
            }

        return {"allowed": True}


organization_service = OrganizationService()
