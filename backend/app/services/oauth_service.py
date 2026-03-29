"""OAuth user creation and linking service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import User, SocialAccount, UserRole
from typing import Optional, Tuple


class OAuthService:
    """Handle OAuth user creation and account linking."""

    @staticmethod
    async def get_or_create_user(
        db: AsyncSession,
        provider: str,
        provider_user_id: str,
        email: str,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        email_verified: bool = False
    ) -> Tuple[User, bool]:
        """
        Get existing user or create new one.
        Returns (user, is_new_user)
        """
        # Try to find by OAuth provider + ID
        result = await db.execute(
            select(User).where(
                User.oauth_provider == provider,
                User.oauth_id == provider_user_id
            )
        )
        user = result.scalar_one_or_none()

        if user:
            # Update profile if missing
            if name and not user.name:
                user.name = name
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            if email_verified and not user.email_verified:
                user.email_verified = email_verified
            await db.commit()
            await db.refresh(user)
            return user, False

        # Try to find by email (link existing account)
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if user:
            # Link OAuth to existing account
            user.oauth_provider = provider
            user.oauth_id = provider_user_id
            if name and not user.name:
                user.name = name
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            if email_verified:
                user.email_verified = email_verified

            # Create social account record
            social = SocialAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=email,
                profile_data={'name': name, 'avatar_url': avatar_url}
            )
            db.add(social)
            await db.commit()
            await db.refresh(user)
            return user, False

        # Create new user (auto-registration)
        user = User(
            email=email,
            email_verified=email_verified,
            oauth_provider=provider,
            oauth_id=provider_user_id,
            name=name or email.split('@')[0],
            avatar_url=avatar_url,
            role=UserRole.USER,
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Create social account record
        social = SocialAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=email,
            profile_data={'name': name, 'avatar_url': avatar_url}
        )
        db.add(social)
        await db.commit()

        return user, True
