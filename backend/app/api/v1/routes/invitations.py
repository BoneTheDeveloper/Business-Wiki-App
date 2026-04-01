"""Invitation management API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.models.database import get_db
from app.models.models import User, OrgRole
from app.schemas.invitation import (
    InvitationCreate, InvitationResponse, InvitationAccept,
    InvitationList,
)
from app.dependencies import get_current_user
from app.services.invitation_service import invitation_service
from app.services.organization_service import organization_service
from app.services.permission_service import permission_service, Permission

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post("/organizations/{org_id}/invite", response_model=InvitationResponse, status_code=201)
async def create_invitation(
    org_id: UUID,
    data: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send an invitation to join organization.

    Requires invite permission. Returns invitation with token for email sending.
    """
    # Check permission
    if not await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.INVITE
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions to invite")

    # Cannot invite as owner
    if data.role == OrgRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot invite members as owner")

    try:
        invitation, raw_token = await invitation_service.create_invitation(
            db=db,
            org_id=org_id,
            invitee_email=data.invitee_email,
            role=data.role,
            invited_by_id=current_user.id
        )
        await db.commit()

        # In production, send email here with raw_token
        # For now, return token in response (remove in production!)
        response = InvitationResponse.model_validate(invitation)
        return response
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/organizations/{org_id}", response_model=InvitationList)
async def list_organization_invitations(
    org_id: UUID,
    include_used: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List pending invitations for organization (admin+ only)."""
    if not await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.INVITE
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    invitations = await invitation_service.get_organization_invitations(
        db=db,
        org_id=org_id,
        include_used=include_used
    )

    return InvitationList(
        items=[InvitationResponse.model_validate(inv) for inv in invitations],
        total=len(invitations)
    )


@router.post("/accept", response_model=dict)
async def accept_invitation(
    data: InvitationAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept an invitation with token.

    The current user's email must match the invitation email.
    """
    try:
        org = await invitation_service.accept_invitation(
            db=db,
            raw_token=data.token,
            user=current_user
        )
        await db.commit()

        return {
            "message": "Invitation accepted successfully",
            "organization_id": str(org.id),
            "organization_name": org.name
        }
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{invitation_id}/resend", response_model=InvitationResponse)
async def resend_invitation(
    invitation_id: UUID,
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resend an invitation (generates new token)."""
    if not await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.INVITE
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        invitation, raw_token = await invitation_service.resend_invitation(
            db=db,
            invitation_id=invitation_id,
            org_id=org_id
        )
        await db.commit()

        # In production, send email here
        return InvitationResponse.model_validate(invitation)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{invitation_id}")
async def cancel_invitation(
    invitation_id: UUID,
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a pending invitation."""
    if not await permission_service.has_org_permission(
        db, org_id, current_user.id, Permission.INVITE
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        cancelled = await invitation_service.cancel_invitation(
            db=db,
            invitation_id=invitation_id,
            org_id=org_id
        )
        if not cancelled:
            raise HTTPException(status_code=404, detail="Invitation not found")

        await db.commit()
        return {"message": "Invitation cancelled successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/info/{token}")
async def get_invitation_info(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Get invitation details by token (public, no auth required).

    Used to show invitation preview before accepting.
    """
    invitation = await invitation_service.validate_token(db, token)

    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")

    # Get organization info
    org = await organization_service.get_organization(db, invitation.organization_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "organization_name": org.name,
        "organization_slug": org.slug,
        "invitee_email": invitation.invitee_email,
        "role": invitation.role,
        "expires_at": invitation.expires_at,
        "is_valid": True
    }
