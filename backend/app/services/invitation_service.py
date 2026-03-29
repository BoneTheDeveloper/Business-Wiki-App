"""Invitation management service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
import secrets
import hashlib
import uuid as uuid_module

from app.models.models import (
    Organization, OrganizationMember, User, Invitation,
    OrgRole
)
from app.services.organization_service import organization_service


class InvitationService:
    """Service for invitation management operations."""

    # Token settings
    TOKEN_LENGTH = 32  # Bytes for random token
    TOKEN_EXPIRY_DAYS = 7
    MAX_INVITATIONS_PER_HOUR = 5  # Rate limit per org

    @staticmethod
    def _generate_token() -> tuple[str, str, str]:
        """Generate secure token with salt and hash.

        Returns:
            tuple: (raw_token, token_hash, token_salt)
        """
        # Generate random salt
        salt = secrets.token_hex(32)

        # Generate random token
        raw_token = secrets.token_urlsafe(InvitationService.TOKEN_LENGTH)

        # Hash token with salt
        token_hash = hashlib.sha256(f"{raw_token}{salt}".encode()).hexdigest()

        return raw_token, token_hash, salt

    @staticmethod
    def _hash_token(raw_token: str, salt: str) -> str:
        """Hash a token with salt for verification."""
        return hashlib.sha256(f"{raw_token}{salt}".encode()).hexdigest()

    @staticmethod
    async def check_rate_limit(db: AsyncSession, org_id: UUID) -> bool:
        """Check if organization has exceeded invitation rate limit."""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        result = await db.execute(
            select(func.count(Invitation.id)).where(
                Invitation.organization_id == org_id,
                Invitation.created_at >= one_hour_ago
            )
        )
        count = result.scalar() or 0

        return count < InvitationService.MAX_INVITATIONS_PER_HOUR

    @staticmethod
    async def create_invitation(
        db: AsyncSession,
        org_id: UUID,
        invitee_email: str,
        role: OrgRole,
        invited_by_id: UUID
    ) -> tuple[Invitation, str]:
        """Create an invitation.

        Returns:
            tuple: (Invitation object, raw_token for sending in email)
        """
        # Check rate limit
        if not await InvitationService.check_rate_limit(db, org_id):
            raise ValueError("Invitation rate limit exceeded. Please wait before sending more invitations.")

        # Normalize email
        invitee_email = invitee_email.lower().strip()

        # Check if user is already a member
        existing_user = await db.execute(
            select(User).where(User.email == invitee_email)
        )
        user = existing_user.scalar_one_or_none()

        if user:
            is_member = await organization_service.is_member(db, org_id, user.id)
            if is_member:
                raise ValueError("User is already a member of this organization")

        # Check for existing pending invitation
        existing = await db.execute(
            select(Invitation).where(
                Invitation.organization_id == org_id,
                Invitation.invitee_email == invitee_email,
                Invitation.used == False,
                Invitation.expires_at > datetime.utcnow()
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Pending invitation already exists for this email")

        # Generate token
        raw_token, token_hash, token_salt = InvitationService._generate_token()

        # Create invitation
        invitation = Invitation(
            id=uuid_module.uuid4(),
            organization_id=org_id,
            invitee_email=invitee_email,
            role=role,
            token_hash=token_hash,
            token_salt=token_salt,
            invited_by_id=invited_by_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=InvitationService.TOKEN_EXPIRY_DAYS),
            used=False
        )
        db.add(invitation)
        await db.flush()

        return invitation, raw_token

    @staticmethod
    async def validate_token(
        db: AsyncSession,
        raw_token: str
    ) -> Optional[Invitation]:
        """Validate invitation token and return invitation if valid."""
        # Get all unused non-expired invitations
        result = await db.execute(
            select(Invitation).where(
                Invitation.used == False,
                Invitation.expires_at > datetime.utcnow()
            )
        )
        invitations = result.scalars().all()

        # Check each invitation (need to check hash with salt)
        for inv in invitations:
            expected_hash = InvitationService._hash_token(raw_token, inv.token_salt)
            if secrets.compare_digest(expected_hash, inv.token_hash):
                return inv

        return None

    @staticmethod
    async def accept_invitation(
        db: AsyncSession,
        raw_token: str,
        user: User
    ) -> Organization:
        """Accept an invitation and add user to organization."""
        # Validate token
        invitation = await InvitationService.validate_token(db, raw_token)

        if not invitation:
            raise ValueError("Invalid or expired invitation token")

        # Check email matches (if user already exists)
        if user.email.lower() != invitation.invitee_email.lower():
            raise ValueError("This invitation was sent to a different email address")

        # Mark invitation as used
        invitation.used = True
        invitation.used_at = datetime.utcnow()

        # Add user to organization
        member = await organization_service.add_member(
            db=db,
            org_id=invitation.organization_id,
            user_id=user.id,
            role=invitation.role,
            invited_by_id=invitation.invited_by_id
        )

        # Get organization
        org = await organization_service.get_organization(db, invitation.organization_id)

        await db.flush()

        return org

    @staticmethod
    async def get_organization_invitations(
        db: AsyncSession,
        org_id: UUID,
        include_used: bool = False
    ) -> list[Invitation]:
        """List invitations for an organization."""
        query = select(Invitation).where(
            Invitation.organization_id == org_id
        )

        if not include_used:
            query = query.where(Invitation.used == False)

        query = query.order_by(Invitation.created_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def cancel_invitation(
        db: AsyncSession,
        invitation_id: UUID,
        org_id: UUID
    ) -> bool:
        """Cancel (delete) a pending invitation."""
        result = await db.execute(
            select(Invitation).where(
                Invitation.id == invitation_id,
                Invitation.organization_id == org_id,
                Invitation.used == False
            )
        )
        invitation = result.scalar_one_or_none()

        if not invitation:
            return False

        await db.delete(invitation)
        await db.flush()
        return True

    @staticmethod
    async def resend_invitation(
        db: AsyncSession,
        invitation_id: UUID,
        org_id: UUID
    ) -> tuple[Invitation, str]:
        """Resend an invitation (generates new token)."""
        result = await db.execute(
            select(Invitation).where(
                Invitation.id == invitation_id,
                Invitation.organization_id == org_id,
                Invitation.used == False
            )
        )
        invitation = result.scalar_one_or_none()

        if not invitation:
            raise ValueError("Invitation not found or already used")

        # Check rate limit
        if not await InvitationService.check_rate_limit(db, org_id):
            raise ValueError("Invitation rate limit exceeded")

        # Generate new token
        raw_token, token_hash, token_salt = InvitationService._generate_token()

        # Update invitation
        invitation.token_hash = token_hash
        invitation.token_salt = token_salt
        invitation.created_at = datetime.utcnow()
        invitation.expires_at = datetime.utcnow() + timedelta(days=InvitationService.TOKEN_EXPIRY_DAYS)

        await db.flush()

        return invitation, raw_token


invitation_service = InvitationService()
