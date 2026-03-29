# Phase 6: Testing & Documentation

**Priority:** P1 | **Status:** Pending | **Effort:** 1h

## Context

- Research: `plans/reports/researcher-260327-1108-google-oauth-implementation.md`
- Depends on: Phase 5 (Security Hardening)
- Tests: `backend/tests/`
- Docs: `docs/`

## Overview

Write comprehensive tests for OAuth flow and finalize documentation.

## Key Insights

1. Mock Google OAuth responses for unit tests
2. Integration tests verify full flow
3. Frontend tests cover callback handling
4. Documentation must be complete for handoff

## Requirements

### Functional
- Unit tests for OAuth service
- Integration tests for OAuth endpoints
- Frontend tests for callback view
- API documentation updated

### Non-Functional
- >80% code coverage on OAuth code
- Tests run in CI pipeline

## Architecture

```
Test Coverage:
┌─────────────────────────────────────────────────┐
│ Backend Unit Tests                               │
│ ├── OAuthService.get_or_create_user()           │
│ ├── Token creation/rotation                      │
│ └── Rate limiting logic                          │
├─────────────────────────────────────────────────┤
│ Backend Integration Tests                        │
│ ├── GET /oauth/authorize                         │
│ ├── GET /oauth/callback (success)                │
│ ├── GET /oauth/callback (errors)                 │
│ └── POST /auth/refresh (rotation)                │
├─────────────────────────────────────────────────┤
│ Frontend Tests                                   │
│ ├── AuthStore.oauthLogin()                       │
│ ├── OAuthCallbackView component                  │
│ └── LoginView OAuth button                       │
└─────────────────────────────────────────────────┘
```

## Related Code Files

### Create
- `backend/tests/test_oauth_service.py` - Service unit tests
- `backend/tests/test_oauth_routes.py` - Integration tests
- `frontend/src/__tests__/oauth.spec.ts` - Frontend tests

### Modify
- `docs/api-documentation.md` - Add OAuth endpoints
- `README.md` - Update with OAuth info

## Implementation Steps

### Step 1: Backend Unit Tests

```python
# backend/tests/test_oauth_service.py

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.oauth_service import OAuthService
from app.models.models import User, UserRole

@pytest.mark.asyncio
async def test_get_or_create_user_new_user(db: AsyncSession):
    """Test creating new user from OAuth."""
    user, is_new = await OAuthService.get_or_create_user(
        db=db,
        provider='google',
        provider_user_id='google-123',
        email='newuser@example.com',
        name='New User',
        avatar_url='https://example.com/avatar.jpg',
        email_verified=True
    )

    assert is_new is True
    assert user.email == 'newuser@example.com'
    assert user.name == 'New User'
    assert user.oauth_provider == 'google'
    assert user.oauth_id == 'google-123'
    assert user.email_verified is True
    assert user.password_hash is None


@pytest.mark.asyncio
async def test_get_or_create_user_existing_by_oauth(db: AsyncSession):
    """Test finding existing user by OAuth ID."""
    # Create user first
    user, _ = await OAuthService.get_or_create_user(
        db=db,
        provider='google',
        provider_user_id='google-456',
        email='existing@example.com',
        name='Existing User'
    )

    # Find same user
    found_user, is_new = await OAuthService.get_or_create_user(
        db=db,
        provider='google',
        provider_user_id='google-456',
        email='existing@example.com'
    )

    assert is_new is False
    assert found_user.id == user.id


@pytest.mark.asyncio
async def test_get_or_create_user_link_by_email(db: AsyncSession, existing_user: User):
    """Test linking OAuth to existing user by email."""
    user, is_new = await OAuthService.get_or_create_user(
        db=db,
        provider='google',
        provider_user_id='google-789',
        email=existing_user.email,
        name='Linked Name'
    )

    assert is_new is False
    assert user.id == existing_user.id
    assert user.oauth_provider == 'google'
    assert user.oauth_id == 'google-789'


@pytest.mark.asyncio
async def test_update_missing_profile_data(db: AsyncSession):
    """Test updating missing profile data on OAuth login."""
    # Create user without name/avatar
    user, _ = await OAuthService.get_or_create_user(
        db=db,
        provider='google',
        provider_user_id='google-111',
        email='noprofile@example.com'
    )

    assert user.name is None

    # Login again with profile data
    updated_user, _ = await OAuthService.get_or_create_user(
        db=db,
        provider='google',
        provider_user_id='google-111',
        email='noprofile@example.com',
        name='Now Has Name',
        avatar_url='https://example.com/new.jpg'
    )

    assert updated_user.name == 'Now Has Name'
    assert updated_user.avatar_url == 'https://example.com/new.jpg'
```

### Step 2: Backend Integration Tests

```python
# backend/tests/test_oauth_routes.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

@pytest.fixture
def mock_oauth_token():
    return {
        'access_token': 'mock-access-token',
        'token_type': 'Bearer',
        'userinfo': {
            'sub': 'google-user-123',
            'email': 'test@example.com',
            'name': 'Test User',
            'picture': 'https://example.com/pic.jpg',
            'email_verified': True
        }
    }


def test_oauth_authorize_redirects(client: TestClient):
    """Test authorize endpoint redirects to Google."""
    response = client.get('/api/v1/oauth/authorize', follow_redirects=False)

    assert response.status_code == 302
    assert 'accounts.google.com' in response.headers['location']


def test_oauth_callback_missing_params(client: TestClient):
    """Test callback with missing parameters."""
    response = client.get('/api/v1/oauth/callback')

    assert response.status_code == 422  # Validation error


def test_oauth_callback_error_param(client: TestClient):
    """Test callback with OAuth error."""
    response = client.get(
        '/api/v1/oauth/callback',
        params={'error': 'access_denied', 'error_description': 'User denied'}
    )

    assert response.status_code == 400
    assert 'access_denied' in response.json()['detail']


def test_oauth_callback_invalid_state(client: TestClient):
    """Test callback with invalid state parameter."""
    response = client.get(
        '/api/v1/oauth/callback',
        params={'code': 'test-code', 'state': 'invalid-state'}
    )

    assert response.status_code == 400
    assert 'Invalid state' in response.json()['detail']


@patch('app.auth.oauth_routes.oauth.google.authorize_access_token')
def test_oauth_callback_success(mock_auth, client: TestClient, mock_oauth_token):
    """Test successful OAuth callback."""
    mock_auth.return_value = mock_oauth_token

    # First get authorize to set session state
    auth_response = client.get('/api/v1/oauth/authorize', follow_redirects=False)
    # Extract state from redirect URL or session

    # Mock the callback
    with client.session_transaction() as session:
        session['oauth_state'] = 'test-state'

    response = client.get(
        '/api/v1/oauth/callback',
        params={'code': 'test-code', 'state': 'test-state'}
    )

    assert response.status_code == 200
    data = response.json()
    assert 'access_token' in data
    assert 'refresh_token' in data
    assert data['user']['email'] == 'test@example.com'


def test_rate_limiting_oauth(client: TestClient):
    """Test rate limiting on OAuth endpoints."""
    for _ in range(15):
        response = client.get('/api/v1/oauth/authorize', follow_redirects=False)

    # Should be rate limited after 10 requests
    assert response.status_code == 429
```

### Step 3: Frontend Tests

```typescript
// frontend/src/__tests__/oauth.spec.ts

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth-store'
import api from '@/api/client'

vi.mock('@/api/client')

describe('OAuth Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('oauthLogin', () => {
    it('should exchange code for tokens', async () => {
      const mockResponse = {
        access_token: 'test-access',
        refresh_token: 'test-refresh',
        user: {
          id: '123',
          email: 'test@example.com',
          role: 'user',
          is_active: true,
          created_at: '2024-01-01'
        },
        is_new_user: false
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const store = useAuthStore()
      const result = await store.oauthLogin('test-code', 'test-state')

      expect(result).toBe(true)
      expect(store.accessToken).toBe('test-access')
      expect(store.user?.email).toBe('test@example.com')
    })

    it('should handle OAuth error', async () => {
      vi.mocked(api.get).mockRejectedValue({
        response: { data: { detail: 'OAuth failed' } }
      })

      const store = useAuthStore()
      const result = await store.oauthLogin('bad-code', 'bad-state')

      expect(result).toBe(false)
      expect(store.error).toBe('OAuth failed')
    })
  })

  describe('initOAuth', () => {
    it('should redirect to OAuth authorize', () => {
      const store = useAuthStore()

      // Mock window.location
      const originalLocation = window.location
      delete (window as any).location
      window.location = { href: '' } as any

      store.initOAuth()

      expect(window.location.href).toBe('/api/v1/oauth/authorize')

      window.location = originalLocation
    })
  })
})
```

### Step 4: Update API Documentation

```markdown
# docs/api-documentation.md (add section)

## OAuth Endpoints

### GET /api/v1/oauth/authorize

Initiates Google OAuth flow. Redirects user to Google consent screen.

**Response:** 302 Redirect to Google OAuth

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/oauth/authorize"
# Redirects to: https://accounts.google.com/o/oauth2/v2/auth?...
```

---

### GET /api/v1/oauth/callback

Handles OAuth callback from Google. Exchanges authorization code for tokens.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| code | string | Yes | Authorization code from Google |
| state | string | Yes | State parameter for CSRF validation |

**Response:** 200 OK

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "role": "user",
    "is_active": true,
    "email_verified": true,
    "name": "User Name",
    "avatar_url": "https://...",
    "created_at": "2024-01-01T00:00:00"
  },
  "is_new_user": false
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid state, missing parameters, OAuth error |
| 403 | Account disabled |
| 429 | Rate limited (too many requests) |

---

### OAuth Flow Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │────▶│  Server  │────▶│  Google  │
│          │     │/authorize│     │  OAuth   │
└──────────┘     └──────────┘     └──────────┘
      │                                │
      │                                │
      │         ┌──────────┐           │
      │         │  Server  │◀──────────┘
      └────────▶│/callback │ (code + state)
                └──────────┘
                      │
                      ▼
                ┌──────────┐
                │  Tokens  │
                │  + User  │
                └──────────┘
```
```

### Step 5: Update README

```markdown
# README.md (add section)

## Google OAuth Setup

### Quick Setup

1. Follow the [OAuth Setup Guide](docs/oauth-setup-guide.md)
2. Add credentials to `.env`:
   ```env
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```
3. Restart the backend service

### Testing OAuth

1. Navigate to http://localhost:5173/login
2. Click "Google" button
3. Authorize with your Google account
4. You'll be redirected to the dashboard

### OAuth Features

- Automatic user registration
- Profile data sync (name, avatar)
- Email verification from Google
- Secure PKCE flow
```

## Todo List

- [ ] Create test_oauth_service.py
- [ ] Create test_oauth_routes.py
- [ ] Create oauth.spec.ts
- [ ] Update API documentation
- [ ] Update README with OAuth section
- [ ] Run all tests
- [ ] Verify test coverage >80%
- [ ] Test with real Google credentials

## Success Criteria

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All frontend tests pass
- [ ] Test coverage >80% on OAuth code
- [ ] API documentation complete
- [ ] README updated
- [ ] Full OAuth flow works with real Google

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Mock doesn't match real OAuth | Medium | Integration test with real credentials |
| Test flakiness | Low | Use proper async handling |

## Security Considerations

- Don't use real OAuth credentials in tests
- Mock external services
- Test error paths thoroughly

## Final Checklist

### Implementation Complete
- [ ] Database migration applied
- [ ] Backend OAuth endpoints working
- [ ] Frontend OAuth integration working
- [ ] Environment configuration documented
- [ ] Security hardening applied
- [ ] Tests passing
- [ ] Documentation complete

### Production Ready
- [ ] HTTPS enabled
- [ ] Different OAuth credentials for prod
- [ ] Rate limiting tuned
- [ ] Audit logging enabled
- [ ] Monitoring configured

## Summary

Google OAuth integration is complete. Users can now:
- Login with Google account
- Auto-register with Google profile
- Link existing accounts by email
- Enjoy secure PKCE flow

Total implementation effort: ~8 hours
