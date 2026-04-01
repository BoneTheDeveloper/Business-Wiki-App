"""Permission checking service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Optional
from uuid import UUID
from enum import Enum

from app.models.models import (
    Organization, OrganizationMember, Document, DocumentAccess,
    Group, GroupMember, User, OrgRole, DocumentVisibility, AccessLevel
)


class Permission(str, Enum):
    """Permission types."""
    VIEW = "view"
    EDIT = "edit"
    DELETE = "delete"
    MANAGE = "manage"  # Manage organization settings
    INVITE = "invite"  # Invite members
    CREATE_GROUP = "create_group"


class PermissionService:
    """Service for permission checking operations."""

    # Role hierarchy for comparison
    ROLE_HIERARCHY = {
        OrgRole.OWNER: 4,
        OrgRole.ADMIN: 3,
        OrgRole.MEMBER: 2,
        OrgRole.VIEWER: 1,
    }

    # Permissions granted per role (static mapping)
    ROLE_PERMISSIONS = {
        OrgRole.OWNER: [
            Permission.VIEW, Permission.EDIT, Permission.DELETE,
            Permission.MANAGE, Permission.INVITE, Permission.CREATE_GROUP
        ],
        OrgRole.ADMIN: [
            Permission.VIEW, Permission.EDIT, Permission.DELETE,
            Permission.INVITE, Permission.CREATE_GROUP
        ],
        OrgRole.MEMBER: [
            Permission.VIEW, Permission.EDIT, Permission.CREATE_GROUP
        ],
        OrgRole.VIEWER: [
            Permission.VIEW
        ],
    }

    @staticmethod
    def get_role_level(role: OrgRole) -> int:
        """Get numeric level for role."""
        return PermissionService.ROLE_HIERARCHY.get(role, 0)

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
    async def has_org_permission(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID,
        permission: Permission
    ) -> bool:
        """Check if user has specific permission in organization."""
        role = await PermissionService.get_member_role(db, org_id, user_id)

        if not role:
            return False

        return permission in PermissionService.ROLE_PERMISSIONS.get(role, [])

    @staticmethod
    async def can_manage_member(
        db: AsyncSession,
        org_id: UUID,
        actor_id: UUID,
        target_user_id: UUID,
        target_role: Optional[OrgRole] = None
    ) -> bool:
        """Check if actor can manage target user's membership."""
        actor_role = await PermissionService.get_member_role(db, org_id, actor_id)
        target_role_in_org = await PermissionService.get_member_role(db, org_id, target_user_id)

        if not actor_role or not target_role_in_org:
            return False

        actor_level = PermissionService.get_role_level(actor_role)
        target_level = PermissionService.get_role_level(target_role_in_org)

        # Actor must have higher or equal level (but can't manage same level unless owner)
        if actor_role == OrgRole.OWNER:
            return True

        # Admins can manage members and viewers
        if actor_role == OrgRole.ADMIN:
            return target_role_in_org in [OrgRole.MEMBER, OrgRole.VIEWER]

        return False

    @staticmethod
    async def check_document_access(
        db: AsyncSession,
        document: Document,
        user_id: UUID,
        required_level: AccessLevel = AccessLevel.VIEW
    ) -> bool:
        """Check if user can access document with required level."""
        # Document owner always has access
        if document.user_id == user_id:
            return True

        # If no organization, only owner has access
        if not document.organization_id:
            return False

        # Get user's role in organization
        org_role = await PermissionService.get_member_role(
            db, document.organization_id, user_id
        )

        if not org_role:
            return False

        # Organization owner/admin always has access
        if org_role in [OrgRole.OWNER, OrgRole.ADMIN]:
            return True

        # Check visibility-based access
        if document.visibility == DocumentVisibility.PUBLIC:
            # All org members can view public documents
            if required_level == AccessLevel.VIEW:
                return True
            # Edit requires member+ role for public docs
            return org_role in [OrgRole.MEMBER, OrgRole.ADMIN, OrgRole.OWNER]

        if document.visibility == DocumentVisibility.PRIVATE:
            # Private docs: only owner and admins (already checked above)
            return False

        if document.visibility == DocumentVisibility.RESTRICTED:
            # Check explicit access grants
            return await PermissionService._check_explicit_access(
                db, document.id, user_id, required_level
            )

        return False

    @staticmethod
    def _has_sufficient_access(
        grant_level: AccessLevel,
        required_level: AccessLevel
    ) -> bool:
        """Check if a grant level satisfies the required access level."""
        return required_level == AccessLevel.VIEW or grant_level == AccessLevel.EDIT

    @staticmethod
    async def _check_explicit_access(
        db: AsyncSession,
        document_id: UUID,
        user_id: UUID,
        required_level: AccessLevel
    ) -> bool:
        """Check explicit access grants for restricted documents."""
        # Check direct user access
        user_access = await db.execute(
            select(DocumentAccess).where(
                DocumentAccess.document_id == document_id,
                DocumentAccess.user_id == user_id
            )
        )
        access = user_access.scalar_one_or_none()

        if access and PermissionService._has_sufficient_access(access.access_level, required_level):
            return True

        # Check group-based access
        group_access = await db.execute(
            select(DocumentAccess)
            .join(Group)
            .join(GroupMember)
            .where(
                DocumentAccess.document_id == document_id,
                GroupMember.user_id == user_id
            )
        )
        group_grants = group_access.scalars().all()

        for grant in group_grants:
            if PermissionService._has_sufficient_access(grant.access_level, required_level):
                return True

        return False

    @staticmethod
    async def get_accessible_documents_query(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID
    ):
        """Build query for documents accessible to user in organization."""
        # Get user's role
        org_role = await PermissionService.get_member_role(db, org_id, user_id)

        if not org_role:
            return None

        # Owner/Admin: all documents
        if org_role in [OrgRole.OWNER, OrgRole.ADMIN]:
            return select(Document).where(Document.organization_id == org_id)

        # Member/Viewer: public + own + explicitly granted
        query = select(Document).where(
            Document.organization_id == org_id,
            or_(
                Document.visibility == DocumentVisibility.PUBLIC,
                Document.user_id == user_id,
                # Restricted docs with explicit access via subquery
                Document.id.in_(
                    select(DocumentAccess.document_id).where(
                        or_(
                            DocumentAccess.user_id == user_id,
                            DocumentAccess.group_id.in_(
                                select(GroupMember.group_id).where(
                                    GroupMember.user_id == user_id
                                )
                            )
                        )
                    )
                )
            )
        )

        return query

    @staticmethod
    async def can_upload_to_organization(
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID
    ) -> bool:
        """Check if user can upload documents to organization."""
        return await PermissionService.has_org_permission(
            db, org_id, user_id, Permission.EDIT
        )

    @staticmethod
    async def can_modify_document(
        db: AsyncSession,
        document: Document,
        user_id: UUID
    ) -> bool:
        """Check if user can modify (edit/delete) document."""
        return await PermissionService.check_document_access(
            db, document, user_id, AccessLevel.EDIT
        )


permission_service = PermissionService()
