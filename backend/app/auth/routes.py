"""Authentication API routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import get_db
from app.models.models import User, UserRole
from app.models.schemas import UserRegister, UserLogin, Token, TokenRefresh, UserResponse
from app.auth.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token
)
from app.auth.oauth import oauth
from app.services.oauth_service import OAuthService
from app.dependencies import get_current_user
from app.config import settings
import secrets

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.USER
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login and receive JWT tokens."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled"
        )

    token_data = {"sub": str(user.id), "role": user.role.value}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data)
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(data: TokenRefresh):
    """Refresh access token using refresh token."""
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    token_data = {"sub": payload["sub"], "role": payload["role"]}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return current_user


# OAuth Routes
@router.get("/oauth/google")
async def oauth_google_login(request: Request):
    """Redirect to Google OAuth authorization."""
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state

    # Generate PKCE code verifier and challenge
    code_verifier = secrets.token_urlsafe(64)
    request.session['code_verifier'] = code_verifier

    # Redirect to Google OAuth
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        state=state,
        code_verifier=code_verifier
    )


@router.get("/oauth/callback")
async def oauth_google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback."""
    # Validate state parameter
    state = request.query_params.get('state')
    session_state = request.session.get('oauth_state')

    if not state or state != session_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )

    # Exchange code for token with PKCE
    code_verifier = request.session.get('code_verifier')
    token = await oauth.google.authorize_access_token(
        request,
        code_verifier=code_verifier
    )

    # Get user info from Google
    user_info = token.get('userinfo')
    if not user_info:
        # Fetch user info if not in token
        resp = await oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
        user_info = resp.json()

    # Extract user data
    email = user_info.get('email')
    provider_user_id = user_info.get('sub')
    name = user_info.get('name')
    avatar_url = user_info.get('picture')
    email_verified = user_info.get('email_verified', False)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by OAuth provider"
        )

    # Get or create user
    user, is_new = await OAuthService.get_or_create_user(
        db=db,
        provider='google',
        provider_user_id=provider_user_id,
        email=email,
        name=name,
        avatar_url=avatar_url,
        email_verified=email_verified
    )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled"
        )

    # Generate JWT tokens
    token_data = {"sub": str(user.id), "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Redirect to frontend with tokens
    frontend_url = f"{settings.APP_URL}/oauth/callback?access_token={access_token}&refresh_token={refresh_token}&is_new_user={is_new}"
    return RedirectResponse(url=frontend_url)

