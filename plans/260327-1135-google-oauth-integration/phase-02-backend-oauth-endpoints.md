# Phase 2: Backend OAuth Endpoints

**Priority:** P1 | **Status:** Pending | **Effort:** 2h

## Context

- Research: `plans/reports/researcher-260327-1108-google-oauth-implementation.md`
- Depends on: Phase 1 (Database Migration)
- Auth routes: `backend/app/auth/routes.py`
- Security utils: `backend/app/auth/security.py`

## Overview

Implement OAuth 2.0 Authorization Code + PKCE flow endpoints for Google authentication. Includes authorize redirect, callback handling, and user creation/linking.

## Key Insights

1. Authlib provides built-in PKCE support via `authorize_access_token()`
2. State parameter must be validated before processing callback
3. Auto-registration creates users without password
4. Email conflict: link OAuth to existing account automatically

## Requirements

### Functional
- `GET /api/v1/oauth/authorize` - Redirect to Google OAuth
- `GET /api/v1/oauth/callback` - Handle Google callback
- State parameter CSRF protection
- PKCE code_verifier validation
- Auto-register new users
- Link existing users by email

### Non-Functional
- Response time < 500ms for callback
- Secure token generation (secrets module)
- Proper error handling and messages

## Architecture

```
OAuth Flow:
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  Vue.js │────▶│ FastAPI │────▶│  Google │────▶│ FastAPI │
│  Login  │     │/authorize│    │  OAuth  │     │/callback│
└─────────┘     └─────────┘     └─────────┘     └─────────┘
                    │                               │
                    │ state, code_verifier          │ code, state
                    │ (session)                     │
                    ▼                               ▼
              ┌─────────────────────────────────────────┐
              │ 1. Validate state                       │
              │ 2. Exchange code for tokens (PKCE)      │
              │ 3. Get user info from Google            │
              │ 4. Find/create user in DB               │
              │ 5. Generate JWT tokens                  │
              │ 6. Return tokens + user                 │
              └─────────────────────────────────────────┘
```

## Related Code Files

### Modify
- `backend/app/config.py` - Add OAuth settings
- `backend/app/auth/routes.py` - Add OAuth routes

### Create
- `backend/app/auth/oauth.py` - OAuth configuration and utilities
- `backend/app/services/oauth_service.py` - User creation/linking logic

## Implementation Steps

### Step 1: Add OAuth Configuration

```python
# backend/app/config.py

class Settings(BaseSettings):
    # ... existing settings ...

    # OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/oauth/callback"
    APP_URL: str = "http://localhost:5173"

    # OAuth Settings
    OAUTH_AUTO_REGISTER: bool = True
```

### Step 2: Install Authlib

```bash
# Add to pyproject.toml
authlib = "^1.3.0"
httpx = "^0.27.0"  # For async HTTP requests
```

### Step 3: Create OAuth Module

```python
# backend/app/auth/oauth.py

from authlib.integrations.starlette_client import OAuth
from app.config import settings

oauth = OAuth()

oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)
```

### Step 4: Create OAuth Service

```python
# backend/app/services/oauth_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import User, SocialAccount, UserRole
from typing import Optional, Tuple

class OAuthService:
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
        return user, True
```

### Step 5: Create OAuth Routes

```python
# backend/app/auth/oauth_routes.py

import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import urlencode

from app.config import settings
from app.models.database import get_db
from app.models.schemas import OAuthCallbackResponse, UserResponse
from app.auth.oauth import oauth
from app.auth.security import create_access_token, create_refresh_token
from app.services.oauth_service import OAuthService

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/authorize")
async def oauth_authorize(request: Request):
    """Redirect to Google OAuth authorization page."""
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in session (requires SessionMiddleware)
    request.session['oauth_state'] = state

    # Build redirect URI
    redirect_uri = settings.GOOGLE_REDIRECT_URI

    # Generate authorization URL
    redirect_response = await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        state=state
    )

    return redirect_response


@router.get("/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback."""
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth error: {error_description or error}"
        )

    # Validate state parameter
    saved_state = request.session.pop('oauth_state', None)
    if not saved_state or state != saved_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    try:
        # Exchange code for tokens (Authlib handles PKCE internally)
        token = await oauth.google.authorize_access_token(request)

        # Get user info from token
        user_info = token.get('userinfo')
        if not user_info:
            # Fetch userinfo if not in token
            resp = await oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo')
            user_info = resp.json()

        email = user_info.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")

        # Get or create user
        user, is_new_user = await OAuthService.get_or_create_user(
            db=db,
            provider='google',
            provider_user_id=user_info.get('sub'),
            email=email,
            name=user_info.get('name'),
            avatar_url=user_info.get('picture'),
            email_verified=user_info.get('email_verified', False)
        )

        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account disabled")

        # Generate JWT tokens
        token_data = {"sub": str(user.id), "role": user.role.value}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return OAuthCallbackResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
            is_new_user=is_new_user
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")
```

### Step 6: Add Session Middleware

```python
# backend/app/main.py

from starlette.middleware.sessions import SessionMiddleware

# Add after CORS middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET_KEY,
    session_cookie="oauth_session",
    max_age=600  # 10 minutes for OAuth flow
)

# Include OAuth router
from app.auth.oauth_routes import router as oauth_router
app.include_router(oauth_router, prefix="/api/v1")
```

## Todo List

- [ ] Add authlib and httpx to dependencies
- [ ] Update config.py with OAuth settings
- [ ] Create oauth.py with Authlib configuration
- [ ] Create oauth_service.py for user management
- [ ] Create oauth_routes.py with endpoints
- [ ] Add SessionMiddleware to main.py
- [ ] Register OAuth router
- [ ] Test authorize endpoint redirects
- [ ] Test callback with mock data

## Success Criteria

- [ ] `/api/v1/oauth/authorize` redirects to Google
- [ ] State parameter stored in session
- [ ] `/api/v1/oauth/callback` validates state
- [ ] PKCE flow completes successfully
- [ ] New users created automatically
- [ ] Existing users linked by email
- [ ] JWT tokens returned correctly
- [ ] Errors handled with appropriate HTTP codes

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Session not persisting | High | Test session middleware config |
| Google API changes | Low | Use stable OIDC endpoints |
| Token exchange failure | Medium | Comprehensive error handling |

## Security Considerations

- State parameter prevents CSRF attacks
- Session cookie httpOnly and secure
- Short session lifetime (10 min) for OAuth flow only
- PKCE prevents code interception attacks

## Next Steps

After completion:
- Proceed to Phase 3: Frontend OAuth Integration
- Test with real Google OAuth credentials
