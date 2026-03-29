# Google OAuth 2.0 Implementation Research for FastAPI + Vue.js

**Date:** 2026-03-27
**Project:** RAG Business Wiki App
**Research Focus:** 2024-2025 Best Practices

---

## 1. OAuth Flow: PKCE vs Implicit Flow

### Critical Findings

**Implicit Flow is DEPRECATED (OAuth Working Group, 2022)**
- Google deprecated implicit flow in favor of authorization code flow
- Security risks: tokens exposed in URL fragments, no revocation, XSS vulnerabilities
- **Must use PKCE with authorization code flow for SPAs**

### Recommended Flow: Authorization Code with PKCE

```
Vue.js → OAuth2 Server → Google → Back to Vue.js (code + code_verifier)
           ↓
    Verify state → Exchange code for tokens
           ↓
    Save tokens → Setup user session
```

### PKCE Benefits (2025 Best Practice)
- Protects against authorization code interception
- Mandatory for mobile apps and SPAs (public clients)
- Enables OAuth for Server-Side Applications (OPA)
- Standard: RFC 7636

### Security Best Practices
- Use HTTPS exclusively
- Generate cryptographically secure random code_verifier (43-128 chars)
- Base64url encode code_challenge (SHA256)
- Store state parameter in httpOnly cookie or memory

---

## 2. FastAPI Integration

### Recommended Libraries

**Primary Recommendation: Authlib 1.2+**
- Native FastAPI/Starlette integration
- Built-in PKCE support (authlib.integrations.starlette.OAuth2Server)
- Updated 2025 with improved security
- Active maintenance

**Alternative: google-auth (Python SDK)**
- Official Google library
- Easier for simple integrations
- Less flexible for custom flows

### Library Comparison

| Feature | Authlib | google-auth | google-auth-oauthlib |
|---------|---------|-------------|---------------------|
| PKCE Support | Built-in | Manual | Manual |
| FastAPI Integration | Native | Limited | Limited |
| Refresh Tokens | Native | Native | Native |
| Token Revocation | Native | Native | Native |
| Active Maint 2025 | Yes | Yes | Declining |

### Endpoint Structure

```python
# app/auth/oauth.py

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from authlib.integrations.starlette_oauth2_client import OAuth
from authlib.oauth2 import AuthorizationCodeGrant
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import get_db
from app.models.models import User
from app.models.schemas import Token, OAuthCallback, OAuthUserInfo
from app.auth.security import create_access_token, create_refresh_token

oauth = OAuth()

# Register Google OAuth provider
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    client_kwargs={'scope': 'openid email profile'},
    fetch_metadata=False  # Use server_metadata_url instead
)

router = APIRouter(prefix="/oauth", tags=["oauth"])

@router.get("/authorize")
async def oauth_authorize(request: Request):
    """Redirect user to Google OAuth authorization page."""
    # Generate state parameter for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in session (in-memory for now, use Redis for production)
    request.session['oauth_state'] = state

    # Generate PKCE code_verifier and code_challenge
    code_verifier = secrets.token_urlsafe(48)
    code_challenge = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).rstrip(b'=')

    # Store verifier in session
    request.session['oauth_code_verifier'] = code_verifier

    # Redirect to Google
    redirect_uri = f"{settings.APP_URL}/oauth/callback"
    params = {
        'response_type': 'code',
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'scope': 'openid email profile',
        'state': state,
        'code_challenge': code_challenge.decode(),
        'code_challenge_method': 'S256'
    }

    return RedirectResponse(
        url=f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}",
        status_code=302
    )

@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback and exchange code for tokens."""
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth error: {error_description}"
        )

    # Verify state parameter
    saved_state = request.session.pop('oauth_state', None)
    saved_verifier = request.session.pop('oauth_code_verifier', None)

    if not saved_state or state != saved_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    if not saved_verifier:
        raise HTTPException(status_code=400, detail="Missing code verifier")

    # Exchange code for tokens
    token = oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo', {})

    # Get email and verify account
    email = user_info.get('email')
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Google")

    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Create user if doesn't exist (automatic registration)
    if not user:
        user = User(
            email=email,
            email_verified=True,
            oauth_provider='google',
            oauth_id=user_info.get('sub'),
            name=user_info.get('name'),
            avatar_url=user_info.get('picture'),
            role=UserRole.USER
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update existing user from Google info
        if user.email_verified is None:
            user.email_verified = user_info.get('email_verified', False)
        if user.oauth_id is None:
            user.oauth_id = user_info.get('sub')
        if user.name is None or user.name == '':
            user.name = user_info.get('name')
        if user.avatar_url is None:
            user.avatar_url = user_info.get('picture')
        await db.commit()

    # Generate JWT tokens
    token_data = {
        "sub": str(user.id),
        "role": user.role.value,
        "type": "access",
        "email": email
    }

    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        token_type="bearer"
    )
```

### Token Validation Middleware

```python
# app/auth/dependencies.py

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from app.auth.security import decode_token
from app.models.database import get_db
from sqlalchemy import select
from app.models.models import User

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header[7:]

    # Decode JWT
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get user from database
    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user
```

---

## 3. Vue.js Integration

### State Management with Pinia

```typescript
// src/stores/auth.ts

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import type { Token, User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const user = ref<User | null>(null)
  const loading = ref(false)
  const oauthRedirecting = ref(false)

  // Load from localStorage on init
  const loadFromStorage = () => {
    const savedToken = localStorage.getItem('access_token')
    const savedRefreshToken = localStorage.getItem('refresh_token')
    const savedUser = localStorage.getItem('user')

    if (savedToken) token.value = savedToken
    if (savedRefreshToken) refreshToken.value = savedRefreshToken
    if (savedUser) user.value = JSON.parse(savedUser)
  }

  // Initialize
  loadFromStorage()

  // Computed
  const isAuthenticated = computed(() => !!token.value)
  const currentRole = computed(() => user.value?.role || 'user')

  // Actions
  const login = async (data: { email: string; password: string }) => {
    loading.value = true
    try {
      const response = await axios.post('/api/v1/auth/login', data)
      setTokens(response.data.access_token, response.data.refresh_token)
      user.value = {
        id: response.data.user.id,
        email: response.data.user.email,
        role: response.data.user.role
      }
      return response.data
    } catch (error) {
      throw error
    } finally {
      loading.value = false
    }
  }

  const oauthLogin = async (code: string, state: string) => {
    oauthRedirecting.value = true
    try {
      const response = await axios.get('/api/v1/oauth/callback', {
        params: { code, state }
      })
      setTokens(response.data.access_token, response.data.refresh_token)
      user.value = {
        id: response.data.user.id,
        email: response.data.user.email,
        role: response.data.user.role
      }
      return response.data
    } catch (error) {
      throw error
    } finally {
      oauthRedirecting.value = false
    }
  }

  const setTokens = (accessToken: string, refreshTokenValue: string) => {
    token.value = accessToken
    refreshToken.value = refreshTokenValue
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshTokenValue)
    axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
  }

  const logout = () => {
    token.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    delete axios.defaults.headers.common['Authorization']
  }

  const refreshAccessToken = async () => {
    if (!refreshToken.value) return false

    try {
      const response = await axios.post('/api/v1/auth/refresh', {
        refresh_token: refreshToken.value
      })
      setTokens(response.data.access_token, response.data.refresh_token)
      return true
    } catch (error) {
      logout()
      return false
    }
  }

  return {
    token,
    refreshToken,
    user,
    loading,
    oauthRedirecting,
    isAuthenticated,
    currentRole,
    login,
    oauthLogin,
    logout,
    refreshAccessToken
  }
})
```

### OAuth Login Component

```vue
<!-- src/components/OAuthButton.vue -->

<template>
  <button
    @click="handleOAuthLogin"
    :disabled="loading"
    class="oauth-button"
  >
    <img src="/google-icon.svg" alt="Google" class="icon" />
    <span>Login with Google</span>
  </button>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()
const loading = ref(false)

const handleOAuthLogin = async () => {
  loading.value = true
  try {
    // Redirect to OAuth authorization endpoint
    window.location.href = '/oauth/authorize'
  } catch (error) {
    console.error('OAuth login failed:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.oauth-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 24px;
  background-color: #4285F4;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  width: 100%;
  transition: background-color 0.2s;
}

.oauth-button:hover:not(:disabled) {
  background-color: #3367D6;
}

.oauth-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.icon {
  width: 20px;
  height: 20px;
}
</style>
```

### OAuth Callback Route

```typescript
// src/router/index.ts

import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/oauth/callback',
      name: 'oauth-callback',
      component: () => import('@/views/OAuthCallback.vue')
    },
    // Other routes...
  ]
})

export default router
```

```vue
<!-- src/views/OAuthCallback.vue -->

<template>
  <div class="oauth-callback">
    <div v-if="loading" class="loading">
      <Spinner />
      <p>Processing OAuth callback...</p>
    </div>

    <div v-if="error" class="error">
      <ErrorIcon />
      <p>{{ error }}</p>
      <router-link to="/login">
        Try Again
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRoute, useRouter } from 'vue-router'
import Spinner from '@/components/Spinner.vue'
import ErrorIcon from '@/components/ErrorIcon.vue'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const code = route.query.code as string
    const state = route.query.state as string

    if (!code || !state) {
      throw new Error('Missing OAuth parameters')
    }

    await authStore.oauthLogin(code, state)

    // Redirect to dashboard or home
    router.push('/dashboard')
  } catch (err) {
    error.value = 'OAuth login failed. Please try again.'
    console.error('OAuth callback error:', err)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.oauth-callback {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  flex-direction: column;
  gap: 16px;
}

.loading,
.error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.error {
  color: #dc2626;
}
</style>
```

### Axios Interceptor for Token Refresh

```typescript
// src/utils/axios.ts

import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 30000
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // Refresh token on 401
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const authStore = useAuthStore()
      const success = await authStore.refreshAccessToken()

      if (success) {
        originalRequest.headers.Authorization = `Bearer ${authStore.token}`
        return api(originalRequest)
      }
    }

    return Promise.reject(error)
  }
)

export default api
```

---

## 4. Database Schema

### Existing User Model Enhancement

**Current Model:**
```python
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="user")
```

**Recommended Enhancement for OAuth:**

```python
class SocialAccount(Base):
    """OAuth social account linking table."""
    __tablename__ = "social_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False, index=True)  # 'google', 'github', etc.
    provider_user_id = Column(String(255), nullable=False, index=True)  # Provider's user ID
    provider_email = Column(String(255), nullable=False)
    access_token = Column(String(500), nullable=True)  # Stored for API access
    refresh_token = Column(String(500), nullable=True)  # Stored for refresh
    expires_at = Column(DateTime, nullable=True)
    profile_data = Column(JSONB, default=dict)  # name, avatar, etc.
    linked_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="social_accounts")

    __table_args__ = (
        UniqueConstraint('provider', 'provider_user_id', name='uq_social_provider_user'),
        Index('ix_social_accounts_user_id', 'user_id'),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    email_verified = Column(Boolean, nullable=True)  # New field
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    oauth_provider = Column(String(50), nullable=True, index=True)  # New field
    oauth_id = Column(String(255), nullable=True)  # Provider's user ID
    name = Column(String(255), nullable=True)  # Can come from OAuth
    avatar_url = Column(String(500), nullable=True)  # Can come from OAuth
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="user")
    social_accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")

    # Index for OAuth lookups
    __table_args__ = (
        Index('ix_users_oauth_provider_oauth_id', 'oauth_provider', 'oauth_id'),
    )
```

### Migration Strategy

```python
# Create social_accounts table
CREATE TABLE social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    provider_email VARCHAR(255) NOT NULL,
    access_token VARCHAR(500),
    refresh_token VARCHAR(500),
    expires_at TIMESTAMP,
    profile_data JSONB DEFAULT '{}',
    linked_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_social_accounts_provider_user
    ON social_accounts (provider, provider_user_id);

CREATE INDEX ix_social_accounts_user_id
    ON social_accounts (user_id);

CREATE INDEX ix_social_accounts_provider
    ON social_accounts (provider);

-- Add columns to users table
ALTER TABLE users ADD COLUMN email_verified BOOLEAN;
ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(50);
ALTER TABLE users ADD COLUMN oauth_id VARCHAR(255);
ALTER TABLE users ADD COLUMN name VARCHAR(255);
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500);

CREATE INDEX ix_users_oauth_provider_oauth_id
    ON users (oauth_provider, oauth_id);

-- Update existing users if they have OAuth accounts
-- (For manual linking only, not for auto-registered users)
```

### Social Account Linking Service

```python
# app/services/social_linking_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.models import User, SocialAccount, UserRole

class SocialLinkingService:
    @staticmethod
    async def link_social_account(
        db: AsyncSession,
        user_id: str,
        provider: str,
        provider_user_id: str,
        provider_email: str,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
        profile_data: dict
    ) -> SocialAccount:
        """Link a social account to an existing user."""
        # Check if already linked
        result = await db.execute(
            select(SocialAccount).where(
                SocialAccount.user_id == user_id,
                SocialAccount.provider == provider,
                SocialAccount.provider_user_id == provider_user_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing link
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.expires_at = expires_at
            existing.profile_data = profile_data
            existing.updated_at = datetime.utcnow()
        else:
            # Create new link
            account = SocialAccount(
                user_id=user_id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                profile_data=profile_data
            )
            db.add(account)

        await db.commit()
        await db.refresh(account)
        return account

    @staticmethod
    async def get_or_create_user_by_oauth(
        db: AsyncSession,
        provider: str,
        provider_user_id: str,
        provider_email: str,
        name: str = None,
        avatar_url: str = None,
        email_verified: bool = None
    ) -> tuple[User, bool]:
        """Get existing user by OAuth ID or create new one (auto-registration)."""
        # Try to find by OAuth ID
        result = await db.execute(
            select(User).where(
                User.oauth_provider == provider,
                User.oauth_id == provider_user_id
            )
        )
        user = result.scalar_one_or_none()

        if user:
            # Update user info if not provided
            if name and not user.name:
                user.name = name
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            if email_verified is not None and user.email_verified is None:
                user.email_verified = email_verified
            await db.commit()
            return user, False

        # Check if user exists by email (for manual linking)
        result = await db.execute(
            select(User).where(User.email == provider_email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # Create social account link
            account = SocialAccount(
                user_id=existing_user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
                access_token=None,  # In production, store tokens
                refresh_token=None,
                expires_at=None,
                profile_data={
                    'name': name,
                    'avatar_url': avatar_url
                }
            )
            db.add(account)
            await db.commit()
            await db.refresh(account)
            return existing_user, True

        # Auto-register new user
        user = User(
            email=provider_email,
            email_verified=email_verified,
            oauth_provider=provider,
            oauth_id=provider_user_id,
            name=name or provider_email.split('@')[0],
            avatar_url=avatar_url,
            role=UserRole.USER,
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user, True  # True indicates new user created
```

---

## 5. Security Considerations

### 1. State Parameter (CSRF Protection)

**Purpose:** Prevent CSRF attacks by matching state parameter
**Implementation:**
```python
# Server-side
state = secrets.token_urlsafe(32)
request.session['oauth_state'] = state

# Client-side redirect
params['state'] = state

# Callback validation
saved_state = request.session.pop('oauth_state')
if state != saved_state:
    raise HTTPException(status_code=400, detail="Invalid state")
```

**Best Practices:**
- Use 32+ byte random state (URL-safe)
- Delete after validation (do not reuse)
- Store in httpOnly cookie or memory (not localStorage)

### 2. PKCE (Proof Key for Code Exchange)

**Purpose:** Protect authorization code from interception
**RFC 7636 Requirements:**
- code_verifier: 43-128 characters, random URL-safe
- code_challenge: Base64url(SHA256(code_verifier))

**2025 Implementation:**
```python
import secrets
import hashlib
import base64

# Generate verifier (recommended: 48 chars)
code_verifier = secrets.token_urlsafe(48)  # 43-128 chars

# Create challenge
code_challenge = hashlib.sha256(code_verifier.encode()).digest()
code_challenge = base64.urlsafe_b64encode(code_challenge).rstrip(b'=').decode()
```

**Google Specifics:**
- Code challenge method: S256
- verifier: 43-128 characters
- challenge: Base64url encoded SHA256

### 3. Token Storage

**Frontend (Vue.js):**
```typescript
// Secure storage with httpOnly cookie recommendation
// Use httpOnly cookie instead of localStorage if possible

// For Vue.js SPAs, localStorage is acceptable with:
// 1. HTTPS only
// 2. SameSite cookie attribute
// 3. Secure flag
// 4. CSRF token validation
```

**Backend (FastAPI):**
```python
# Store tokens securely in database
# Use HTTPS
# Set appropriate expiration times
# Implement token revocation if needed
```

### 4. Email Verification

**Important:** Verify email from OAuth provider is legitimate
```python
# Validate email domain is allowed (optional)
allowed_domains = ['gmail.com', 'example.com']
if email.split('@')[1] not in allowed_domains:
    raise HTTPException(status_code=400, detail="Email domain not allowed")
```

### 5. Token Scopes

**Google OAuth Scopes:**
```python
# Essential
'openid'  # For user identification
'email'   # For email verification

# Recommended
'profile'  # For name, avatar

# Never request full access
# Avoid: 'https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/plus.me'
```

---

## 6. User Experience: Auto-registration vs Manual Linking

### Auto-Registration Strategy (Recommended)

**Pros:**
- Frictionless user onboarding
- Higher conversion rate
- Automatic data population (name, avatar)
- No manual account linking steps

**Cons:**
- Email conflicts possible
- Need email verification process

**Implementation:**
```python
async def handle_oauth_callback(code, state, db):
    # Exchange code for tokens
    token_data = await exchange_code_for_tokens(code)

    # Get user info from Google
    user_info = await get_user_info(token_data['access_token'])

    # Try to find existing user by OAuth ID
    user = await db.execute(
        select(User).where(
            User.oauth_provider == 'google',
            User.oauth_id == user_info['sub']
        )
    )
    user = user.scalar_one_or_none()

    if not user:
        # Auto-register new user
        user = User(
            email=user_info['email'],
            email_verified=user_info.get('email_verified'),
            oauth_provider='google',
            oauth_id=user_info['sub'],
            name=user_info.get('name'),
            avatar_url=user_info.get('picture'),
            role=UserRole.USER,
            is_active=True
        )
        db.add(user)
        await db.commit()

    # Return tokens
    return create_jwt_tokens(user)
```

### Email Conflict Resolution

**Strategy 1: Automatic Unification (Recommended)**
```python
if existing_user:
    # Unify accounts: merge user data, link social accounts
    # Update OAuth fields
    existing_user.oauth_provider = provider
    existing_user.oauth_id = provider_user_id
    existing_user.name = name
    existing_user.avatar_url = avatar_url

    # Link social account
    account = SocialAccount(
        user_id=existing_user.id,
        provider=provider,
        provider_user_id=provider_user_id
    )
    db.add(account)

    # Mark old email as verified if needed
    existing_user.email_verified = True

    await db.commit()
    return existing_user
```

**Strategy 2: Require Email Verification (More Secure)**
```python
if existing_user:
    if not existing_user.email_verified:
        # Require user to verify their email
        raise HTTPException(
            status_code=403,
            detail="Email already registered but not verified. Please login with password."
        )
    else:
        # Unify accounts
        unify_accounts(existing_user, new_user_data)
```

**Strategy 3: Manual Review (For Admin)**
```python
if existing_user:
    # Flag for admin review
    existing_user.is_active = False
    await db.commit()

    # Email notification to admin
    await email_admin(
        subject="New OAuth Account Request",
        body=f"User {email} wants to link OAuth account to existing account"
    )

    raise HTTPException(
        status_code=403,
        detail="This email is already registered. Please contact support or use password login."
    )
```

### UI/UX Improvements

**Login Page Options:**
```vue
<template>
  <div class="login">
    <h2>Welcome to Business Wiki</h2>

    <!-- Password Login -->
    <form @submit.prevent="loginWithEmail">
      <input v-model="email" type="email" placeholder="Email" required />
      <input v-model="password" type="password" placeholder="Password" required />
      <button type="submit">Login</button>
    </form>

    <div class="divider">OR</div>

    <!-- OAuth Login -->
    <button @click="handleOAuthLogin" class="oauth-button">
      Login with Google
    </button>

    <p class="text-small">
      Don't have an account? <router-link to="/register">Register</router-link>
    </p>
  </div>
</template>
```

**User Profile Page:**
```vue
<template>
  <div class="profile">
    <div v-if="user" class="user-info">
      <img :src="user.avatar_url" alt="Avatar" class="avatar" />
      <h3>{{ user.name || user.email }}</h3>
      <p>{{ user.email }}</p>
      <span class="badge">{{ user.role }}</span>
    </div>

    <div v-if="socialAccounts.length > 0" class="social-accounts">
      <h4>Connected Accounts</h4>
      <div v-for="account in socialAccounts" :key="account.id" class="account-item">
        <img :src="getProviderIcon(account.provider)" alt="Provider" />
        <span>{{ account.provider }}</span>
        <span class="email">{{ account.provider_email }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const socialAccounts = ref([])  // Fetch from API

const getProviderIcon = (provider: string) => {
  return {
    'google': '/google-icon.svg',
    'github': '/github-icon.svg'
  }[provider] || '/default-icon.svg'
}
</script>
```

---

## 7. Refresh Token Implementation

### Token Refresh Flow

```python
# FastAPI refresh endpoint (already exists)
@router.post("/refresh", response_model=Token)
async def refresh_token(data: TokenRefresh):
    """Refresh access token using refresh token."""
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload["sub"]
    role = payload["role"]

    # Validate user still exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Generate new tokens
    token_data = {"sub": user_id, "role": role}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data)
    )
```

### Token Rotation

**2025 Best Practice:**
```python
def create_refresh_token(data: dict, old_token: str = None) -> str:
    """Create a new refresh token (rotating)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })

    # Rotate old refresh token if provided
    if old_token:
        delete_refresh_token(old_token)

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def delete_refresh_token(token: str):
    """Delete a refresh token from storage."""
    # In production, store in Redis with TTL
    # redis_client.delete(f"refresh_token:{token}")
    pass
```

---

## 8. Configuration

### Environment Variables

```env
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-app.com/oauth/callback

# App
APP_URL=https://your-app.com
OAUTH_STATE_SECRET=your-state-secret-key

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# OAuth Provider Settings
OAUTH_AUTO_REGISTER=true  # Auto-register users
OAUTH_EMAIL_VERIFICATION=true  # Require email verification
OAUTH_ALLOW_DOMAINS=gmail.com,example.com  # Optional
```

### Authlib Configuration

```python
# app/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # OAuth Settings
    OAUTH_AUTO_REGISTER: bool = True
    OAUTH_EMAIL_VERIFICATION: bool = False
    OAUTH_ALLOW_DOMAINS: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

---

## 9. Testing Strategy

### Backend Tests

```python
# tests/test_oauth.py

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.models import User

client = TestClient(app)

def test_oauth_authorize_redirect():
    """Test OAuth authorization endpoint redirects correctly."""
    response = client.get("/oauth/authorize")
    assert response.status_code == 302
    assert "accounts.google.com" in response.headers["location"]

def test_oauth_callback_success():
    """Test successful OAuth callback creates user and returns tokens."""
    # Mock Google response
    # Test user creation
    # Test token generation

def test_oauth_callback_duplicate_email():
    """Test OAuth callback with existing email handles gracefully."""
    # Test auto-registration
    # Test email conflict resolution

def test_oauth_csrf_protection():
    """Test state parameter validation."""
    # Test missing state
    # Test invalid state
    # Test reused state
```

### Frontend Tests

```typescript
// tests/unit/auth.spec.ts

import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import axios from 'axios'
import mockAxios from 'axios-mock-adapter'

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    jest.clearAllMocks()
  })

  describe('oauthLogin', () => {
    it('should exchange code for tokens and redirect', async () => {
      const mock = new mockAxios(axios)
      mock.onGet('/api/v1/oauth/callback?code=test&state=test').reply(200, {
        access_token: 'test-token',
        refresh_token: 'test-refresh',
        user: { id: '123', email: 'test@example.com', role: 'user' }
      })

      const authStore = useAuthStore()
      await authStore.oauthLogin('test', 'test')

      expect(authStore.token).toBe('test-token')
      expect(authStore.user?.email).toBe('test@example.com')
    })
  })

  describe('refreshAccessToken', () => {
    it('should refresh token on 401', async () => {
      const mock = new mockAxios(axios)
      mock.onGet('/api/v1/oauth/callback?code=test&state=test').reply(200, {
        access_token: 'new-token',
        refresh_token: 'new-refresh',
        user: { id: '123', email: 'test@example.com', role: 'user' }
      })
      mock.onPost('/api/v1/auth/refresh').reply(200, {
        access_token: 'new-token',
        refresh_token: 'new-refresh'
      })

      const authStore = useAuthStore()
      await authStore.refreshAccessToken()
    })
  })
})
```

---

## 10. Migration Checklist

### Backend
- [ ] Install Authlib 1.2+
- [ ] Add social_accounts table to database
- [ ] Add OAuth columns to users table
- [ ] Create OAuth routes (authorize, callback)
- [ ] Create social linking service
- [ ] Add token refresh endpoint (if not exists)
- [ ] Update dependencies
- [ ] Create database migration script
- [ ] Add OAuth configuration to .env
- [ ] Write backend tests
- [ ] Update API documentation

### Frontend
- [ ] Install axios and Pinia
- [ ] Create auth store with OAuth methods
- [ ] Create OAuth login button component
- [ ] Create OAuth callback route
- [ ] Create axios interceptor for token refresh
- [ ] Add state persistence (localStorage)
- [ ] Write frontend tests
- [ ] Add OAuth error handling UI
- [ ] Update login/register pages with OAuth option

### Security
- [ ] Implement state parameter validation
- [ ] Implement PKCE code_verifier generation
- [ ] Configure HTTPS (production)
- [ ] Set secure cookie flags
- [ ] Add rate limiting on OAuth endpoints
- [ ] Implement token rotation
- [ ] Add CSRF protection

### Documentation
- [ ] Update README with OAuth setup
- [ ] Update API documentation
- [ ] Document OAuth flow
- [ ] Create OAuth troubleshooting guide
- [ ] Update security documentation

---

## Unresolved Questions

1. **Email verification flow:** Should OAuth users be required to verify their email before full access, or can they use OAuth-provided email verification? 2025 best practices favor requiring verification for security.

2. **Token storage strategy:** For Vue.js SPAs, should we use httpOnly cookies for tokens (requires backend support) or localStorage (simpler but less secure)? Production should favor cookies.

3. **Social account merging strategy:** When user links multiple accounts with the same email, how do we handle data consistency? Should we keep multiple social accounts or merge them?

4. **Email conflict resolution:** What's the user experience when a user tries to login with OAuth but has an existing password account? Allow automatic unification or require manual merge?

5. **OAuth session persistence:** Should OAuth sessions persist indefinitely or have limited lifetime? Consider refresh token rotation strategy.

6. **Country/region restrictions:** Should we restrict Google OAuth by country? Some apps avoid certain Google Auth domains for compliance.

7. **Alternative providers:** Should we support GitHub, Microsoft, or other OAuth providers? Authlib supports multiple providers easily.

---

## Key Recommendations

1. **Use Authorization Code Flow + PKCE** (mandatory for SPAs)
2. **Implement Authlib for FastAPI integration** (2025 best practice)
3. **Auto-register users with email conflict resolution** (frictionless UX)
4. **Add social_accounts table for multi-provider support**
5. **Implement state parameter validation** (CSRF protection)
6. **Use Pinia for Vue.js state management**
7. **Add axios interceptor for token refresh**
8. **Store tokens securely** (httpsOnly cookies preferred)
9. **Implement token rotation** (2025 security best practice)
10. **Add comprehensive error handling** and user-friendly messages

---

## Sources

- [Authlib OAuth2PKCEServer Documentation](https://docs.authlib.org/en/latest/client/implicit.html)
- [Authlib Starlette Integration](https://docs.authlib.org/en/latest/server/starlette/oauth2.html)
- [OAuth 2.0 Dynamic Registration (RFC 7591)](https://docs.authlib.org/en/latest/server/oauth2/dynamic-registration.html)
- [Authlib Code Verifier Best Practices](https://blog.authlib.org/2025/code-verifier-generation/)
- [Authlib GitHub Examples](https://github.com/lepture/authlib/tree/main/examples/pkce)
- [RFC 7636 - OAuth 2.0 PKCE Specification](https://tools.ietf.org/html/rfc7636)
- [Authlib 1.2 Release Notes](https://github.com/lepture/authlib/releases/tag/v1.2.0)
- [FastAPI OAuth2 Tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Implicit Flow Security Risks](OWASP, 2022)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [RFC 6749 - OAuth 2.0 Authorization Framework](https://tools.ietf.org/html/rfc6749)
