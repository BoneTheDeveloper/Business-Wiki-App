"""FastAPI dependencies for authentication and authorization."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from typing import List

from app.models.database import get_db
from app.models.models import User, UserRole
from app.auth.supabase import verify_supabase_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate Supabase JWT and return the app user."""
    payload = await verify_supabase_token(credentials.credentials)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing sub claim",
        )

    # Look up user in public.users
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    # Auto-create user on first login (belt-and-suspenders with DB trigger)
    if not user:
        email = payload.get("email", "")
        user_metadata = payload.get("user_metadata", {})

        user = User(
            id=user_id,
            email=email,
            email_verified=payload.get("email_confirmed", False),
            name=user_metadata.get("name") or email.split("@")[0],
            avatar_url=user_metadata.get("avatar_url"),
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )

    return user


def require_role(roles: List[UserRole]):
    """Dependency factory to require specific app roles."""
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        # Handle both enum and string comparison for role
        user_role = user.role.value if hasattr(user.role, "value") else user.role
        allowed = [r.value if hasattr(r, "value") else r for r in roles]
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user
    return role_checker


# Common role dependencies
require_admin = require_role([UserRole.ADMIN])
require_editor = require_role([UserRole.ADMIN, UserRole.EDITOR])
require_user = require_role([UserRole.ADMIN, UserRole.EDITOR, UserRole.USER])
