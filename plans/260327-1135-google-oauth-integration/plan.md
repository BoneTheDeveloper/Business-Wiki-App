---
title: "Google OAuth 2.0 Integration"
description: "Full-stack Google OAuth with PKCE, auto-registration, and social account linking"
status: pending
priority: P1
effort: 8h
branch: main
tags: [oauth, authentication, security, fullstack]
created: 2026-03-27
---

# Google OAuth 2.0 Integration

## Overview

Implement Google OAuth 2.0 authentication with Authorization Code + PKCE flow for the RAG Business Wiki App. This enables users to login/register using their Google accounts with automatic account linking and secure token handling.

## Research Reference

- Research report: `plans/reports/researcher-260327-1108-google-oauth-implementation.md`

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| OAuth Flow | Authorization Code + PKCE | Implicit flow deprecated; PKCE required for SPAs |
| Library | Authlib 1.2+ | Native FastAPI/Starlette integration, built-in PKCE |
| User Strategy | Auto-registration | Frictionless onboarding with email conflict resolution |
| Token Storage | localStorage + httpOnly cookies | SPA-friendly with security considerations |
| Email Conflicts | Automatic unification | Link OAuth to existing accounts by email |

## Phases

### Phase 1: Database Migration
**Status:** Pending | **Effort:** 1h | **File:** [phase-01-database-migration.md](./phase-01-database-migration.md)

Add OAuth fields to users table and create social_accounts table for multi-provider support.

**Dependencies:** None

### Phase 2: Backend OAuth Endpoints
**Status:** Pending | **Effort:** 2h | **File:** [phase-02-backend-oauth-endpoints.md](./phase-02-backend-oauth-endpoints.md)

Implement OAuth authorize, callback endpoints with PKCE and state parameter validation.

**Dependencies:** Phase 1

### Phase 3: Frontend OAuth Integration
**Status:** Pending | **Effort:** 2h | **File:** [phase-03-frontend-oauth-integration.md](./phase-03-frontend-oauth-integration.md)

Add OAuth button, callback handler, and update auth store with OAuth methods.

**Dependencies:** Phase 2

### Phase 4: Environment & Configuration
**Status:** Pending | **Effort:** 1h | **File:** [phase-04-environment-configuration.md](./phase-04-environment-configuration.md)

Add OAuth configuration to settings, environment variables, and Google Cloud Console setup.

**Dependencies:** None (parallel with Phase 1)

### Phase 5: Security Hardening
**Status:** Pending | **Effort:** 1h | **File:** [phase-05-security-hardening.md](./phase-05-security-hardening.md)

Implement rate limiting, session management, and security best practices.

**Dependencies:** Phase 2, Phase 3

### Phase 6: Testing & Documentation
**Status:** Pending | **Effort:** 1h | **File:** [phase-06-testing-documentation.md](./phase-06-testing-documentation.md)

Write tests for OAuth flow and create setup guide for Google Cloud Console.

**Dependencies:** Phase 5

## Success Criteria

- [ ] Users can login with Google account
- [ ] New users auto-registered with Google profile data
- [ ] Existing users linked by email automatically
- [ ] PKCE code_verifier properly validated
- [ ] State parameter prevents CSRF attacks
- [ ] Tokens stored securely (localStorage + httpOnly option)
- [ ] OAuth errors handled gracefully in UI
- [ ] All tests pass
- [ ] Setup guide documented

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Email conflict | Medium | Auto-unification strategy with clear UX |
| Token exposure | High | HTTPS only, PKCE, short-lived tokens |
| Google API changes | Low | Use stable OAuth 2.0 endpoints |
| Session fixation | Medium | State parameter validation, session regeneration |

## Security Considerations

1. **PKCE Implementation**: Generate cryptographically secure code_verifier (43-128 chars)
2. **State Parameter**: 32-byte random token, validated on callback
3. **HTTPS Only**: Enforce in production
4. **Token Rotation**: Refresh tokens rotated on each use
5. **Scope Limitation**: Request only `openid email profile`

## Unresolved Questions

1. Should we support additional OAuth providers (GitHub, Microsoft)?
2. Should OAuth tokens be stored in database for API access?
3. What's the policy for email domain restrictions?

## Next Steps

1. Start with Phase 1 (Database Migration)
2. Parallel: Phase 4 (Environment Configuration) - set up Google Cloud Console
3. Continue with Phase 2, 3, 5, 6 sequentially
