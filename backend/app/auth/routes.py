"""Auth routes -- Supabase handles signup/login/OAuth, backend only serves /auth/me."""
from fastapi import APIRouter, Depends

from app.models.database import get_db
from app.schemas.user import UserResponse
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info from Supabase JWT."""
    return current_user
