# Phase 4: Environment & Configuration

**Priority:** P1 | **Status:** Pending | **Effort:** 1h

## Context

- Research: `plans/reports/researcher-260327-1108-google-oauth-implementation.md`
- Depends on: None (can run parallel with Phase 1)
- Config: `backend/app/config.py`
- Env example: `.env.example`

## Overview

Configure OAuth environment variables and create setup guide for Google Cloud Console.

## Key Insights

1. OAuth credentials from Google Cloud Console
2. Redirect URI must match exactly (including trailing slashes)
3. Use environment variables, never hardcode secrets
4. Different credentials for dev/staging/prod

## Requirements

### Functional
- OAuth config in Settings class
- Environment variables documented
- Google Cloud Console setup guide

### Non-Functional
- Secrets not in version control
- Clear documentation for setup

## Architecture

```
Google Cloud Console Setup:
┌─────────────────────────────────────────────────┐
│ 1. Create Project                               │
│ 2. Enable Google+ API / People API              │
│ 3. Configure OAuth Consent Screen               │
│ 4. Create OAuth 2.0 Credentials (Web client)    │
│ 5. Add Authorized Redirect URIs                 │
│ 6. Get Client ID and Client Secret              │
└─────────────────────────────────────────────────┘
```

## Related Code Files

### Modify
- `backend/app/config.py` - Add OAuth settings
- `.env.example` - Document OAuth variables
- `docker-compose.yml` - Pass OAuth env vars

### Create
- `docs/oauth-setup-guide.md` - Google Cloud Console instructions

## Implementation Steps

### Step 1: Update Settings

```python
# backend/app/config.py

class Settings(BaseSettings):
    # ... existing settings ...

    # App URLs
    APP_URL: str = "http://localhost:5173"
    API_URL: str = "http://localhost:8000"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/oauth/callback"

    # OAuth Settings
    OAUTH_AUTO_REGISTER: bool = True
    OAUTH_STATE_SECRET: str = "change-me-oauth-state"

    class Config:
        env_file = ".env"
```

### Step 2: Update .env.example

```env
# .env.example

# ... existing variables ...

# App URLs
APP_URL=http://localhost:5173
API_URL=http://localhost:8000

# Google OAuth (get from Google Cloud Console)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5173/oauth/callback

# OAuth Settings
OAUTH_AUTO_REGISTER=true
OAUTH_STATE_SECRET=your-random-secret-key
```

### Step 3: Update docker-compose.yml

```yaml
# docker-compose.yml

services:
  backend:
    environment:
      # ... existing ...
      - APP_URL=${APP_URL:-http://localhost:5173}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI:-http://localhost:5173/oauth/callback}
      - OAUTH_AUTO_REGISTER=${OAUTH_AUTO_REGISTER:-true}
```

### Step 4: Create OAuth Setup Guide

```markdown
# docs/oauth-setup-guide.md

# Google OAuth 2.0 Setup Guide

This guide walks you through setting up Google OAuth for the RAG Business Wiki App.

## Prerequisites

- Google account
- Access to Google Cloud Console

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: `rag-wiki-app` (or your preferred name)
4. Click "Create"

## Step 2: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type (unless you have Google Workspace)
3. Click "Create"

### App Information
- **App name:** RAG Business Wiki
- **User support email:** Your email
- **App logo:** (optional, upload later)

### App Domain (optional)
- Application home page: `http://localhost:5173`
- Privacy policy: (add when available)
- Terms of service: (add when available)

### Developer Contact
- Email addresses: Your email

4. Click "Save and Continue"

### Scopes
1. Click "Add or Remove Scopes"
2. Select these scopes:
   - `.../auth/userinfo.email` (Email)
   - `.../auth/userinfo.profile` (Profile)
   - `openid` (OpenID)
3. Click "Update" → "Save and Continue"

### Test Users (for External apps in testing)
1. Click "Add Users"
2. Add your email and any test users
3. Click "Save and Continue"

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Select "Web application"

### Configure OAuth Client
- **Name:** RAG Wiki Web Client

### Authorized JavaScript Origins
Add these URLs:
- `http://localhost:5173`
- `http://localhost:8000`
- (Add production URL when deploying)

### Authorized Redirect URIs
Add these URIs:
- `http://localhost:5173/oauth/callback`
- (Add production URI when deploying)

4. Click "Create"

## Step 4: Get Credentials

After creating, you'll see:
- **Client ID:** Copy this
- **Client Secret:** Copy this

## Step 5: Configure Application

Add to your `.env` file:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5173/oauth/callback
```

## Production Configuration

When deploying to production:

1. Update OAuth consent screen with production URLs
2. Add production URLs to Authorized JavaScript Origins:
   - `https://your-domain.com`
3. Add production URI to Authorized Redirect URIs:
   - `https://your-domain.com/oauth/callback`
4. Update environment variables in production

## Troubleshooting

### Error: redirect_uri_mismatch
- Ensure `GOOGLE_REDIRECT_URI` in `.env` matches exactly in Google Console
- Check for trailing slashes
- Verify protocol (http vs https)

### Error: access_denied
- User cancelled the consent screen
- App in testing mode and user not added as test user

### Error: invalid_client
- Check Client ID and Client Secret are correct
- Verify credentials are for "Web application" type

## Security Notes

- Never commit Client Secret to version control
- Use different credentials for dev/staging/prod
- Rotate secrets if compromised
- Review authorized redirect URIs regularly
```

## Todo List

- [ ] Update config.py with OAuth settings
- [ ] Update .env.example with OAuth variables
- [ ] Update docker-compose.yml
- [ ] Create docs/oauth-setup-guide.md
- [ ] Test configuration loads correctly
- [ ] Follow setup guide to create Google credentials

## Success Criteria

- [ ] OAuth settings load from environment
- [ ] .env.example documents all variables
- [ ] Setup guide is complete and accurate
- [ ] Can create Google credentials following guide
- [ ] Configuration works with backend

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Wrong redirect URI | High | Document exact URI format |
| Secrets in git | Critical | Add .env to .gitignore |
| Test user not added | Medium | Document test user requirement |

## Security Considerations

- Never commit secrets to version control
- Use environment variables
- Different credentials per environment
- Regular secret rotation

## Next Steps

After completion:
- Create Google Cloud project and credentials
- Test OAuth flow with real credentials
- Proceed to Phase 5: Security Hardening
