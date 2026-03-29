# Multi-Tenancy Implementation Plan

**Created:** 2026-03-27
**Status:** In Progress
**Priority:** High
**Estimated Effort:** 4-5 weeks
**Related Docs:** [Brainstorm Report](../reports/brainstorm-260327-1209-multi-tenancy-architecture.md)

---

## Overview

Transform the RAG Business Wiki from single-tenant to multi-tenant architecture with organization-based document storage, role-based permissions, and email invitation system.

### Key Features
- ✅ Organization-based document storage
- ✅ 4-level role hierarchy (Owner/Admin/Member/Viewer)
- ✅ 3-tier document visibility (Public/Restricted/Private)
- ✅ Email invitation system with secure tokens
- ✅ Group-based access control
- ✅ Organization quotas

### Success Criteria
- Users can create organizations and invite members
- Documents isolated per organization (RLS enforced)
- Role-based permissions working correctly
- Email invitations functional with 7-day expiry
- Quota limits enforced server-side

---

## Phase Breakdown

| Phase | Focus | Duration | Status |
|-------|-------|----------|--------|
| [Phase 1](./phase-01-database-migration.md) | Database Schema & Migration | Week 1 | ✅ Completed |
| [Phase 2](./phase-02-backend-services.md) | Backend Services & API | Week 2-3 | ✅ Completed |
| [Phase 3](./phase-03-frontend-implementation.md) | Frontend UI & Stores | Week 4 | ✅ Completed |
| [Phase 4](./phase-04-security-rls.md) | Security & RLS | Week 4-5 | 🔄 Pending |
| [Phase 5](./phase-05-testing-deployment.md) | Testing & Deployment | Week 5 | 🔄 Pending |

---

## Dependencies

### Internal
- Existing FastAPI backend structure
- Existing Vue 3 frontend
- PostgreSQL database with pgvector
- MinIO storage system

### External
- Email service provider (SendGrid recommended)
- No new infrastructure required

---

## Risk Assessment

### High Priority Risks

**1. Tenant Data Leakage**
- **Impact:** Critical security breach
- **Mitigation:** RLS + application-level checks + comprehensive testing
- **Owner:** Backend team

**2. Performance Regression**
- **Impact:** Slow queries with RLS enabled
- **Mitigation:** Proper indexing, query optimization, load testing
- **Owner:** Backend team

**3. Migration Failures**
- **Impact:** Data loss or corruption
- **Mitigation:** Backup before migration, rollback scripts, staged rollout
- **Owner:** DevOps

### Medium Priority Risks

**4. Email Deliverability**
- **Impact:** Invitations not received
- **Mitigation:** Use reputable email provider (SendGrid), implement retry logic
- **Owner:** Backend team

**5. Quota Race Conditions**
- **Impact:** Users exceed limits
- **Mitigation:** Database-level atomic operations
- **Owner:** Backend team

---

## Architecture Decisions

### Tenant Isolation
- **Decision:** Shared database with logical separation
- **Rationale:** Cost-effective, simpler maintenance, proven for SMBs
- **Trade-offs:** Requires RLS for security vs. separate DBs for maximum isolation

### Membership Model
- **Decision:** Single organization per user
- **Rationale:** Simpler data model, clearer ownership
- **Trade-offs:** Less flexible vs. multi-org membership

### Permission System
- **Decision:** 4-level role hierarchy with document-level ACLs
- **Rationale:** Balances simplicity with flexibility
- **Trade-offs:** More complex than basic RBAC vs. full ACL system

### Email Invitations
- **Decision:** Token-based with 7-day expiry
- **Rationale:** Secure, trackable, user-friendly
- **Trade-offs:** Requires email service vs. direct member addition

---

## Technical Stack

### Backend
- **Framework:** FastAPI (existing)
- **Database:** PostgreSQL 15 + pgvector (existing)
- **Security:** PostgreSQL RLS + application-level checks
- **Email:** SendGrid (new integration)
- **Caching:** Redis (existing, enhanced)

### Frontend
- **Framework:** Vue 3 + TypeScript (existing)
- **State:** Pinia stores (new: organization-store)
- **UI:** PrimeVue components (existing)

### Infrastructure
- **No new services required**
- **Docker Compose:** Existing setup sufficient

---

## File Structure

### Backend Files to Create
```
backend/app/
├── models/
│   ├── organization.py          # Organization ORM model
│   ├── organization_member.py   # Membership model
│   ├── group.py                 # Group model
│   ├── document_access.py       # Access control model
│   └── invitation.py            # Invitation model
├── api/v1/routes/
│   ├── organizations.py         # Organization endpoints
│   ├── invitations.py           # Invitation endpoints
│   └── groups.py                # Group endpoints
├── services/
│   ├── organization_service.py  # Organization business logic
│   ├── invitation_service.py    # Invitation logic
│   ├── permission_service.py    # Permission checks
│   └── quota_service.py         # Quota management
└── schemas/
    ├── organization.py          # Organization schemas
    ├── invitation.py            # Invitation schemas
    └── group.py                 # Group schemas
```

### Backend Files to Modify
```
backend/app/
├── models/
│   ├── models.py                # Add organization_id to Document
│   └── schemas.py               # Update document schemas
├── api/v1/routes/
│   ├── documents.py             # Add org context, permission checks
│   ├── search.py                # Add org filtering
│   └── chat.py                  # Add org filtering
├── api/deps.py                  # Add RLS context setter
└── migrations/
    └── versions/
        └── xxxx_add_multi_tenancy.py  # Migration script
```

### Frontend Files to Create
```
frontend/src/
├── views/
│   ├── OrganizationDashboardView.vue
│   ├── OrganizationMembersView.vue
│   ├── OrganizationGroupsView.vue
│   └── AcceptInvitationView.vue
├── components/
│   ├── organizations/
│   │   ├── InviteMemberDialog.vue
│   │   ├── MemberList.vue
│   │   ├── GroupManager.vue
│   │   └── QuotaDisplay.vue
│   └── documents/
│       ├── VisibilitySelector.vue
│       ├── DocumentAccessManager.vue
│       └── GroupSelector.vue
├── stores/
│   └── organization-store.ts    # Organization state
└── api/
    └── organization-api.ts      # Organization API client
```

### Frontend Files to Modify
```
frontend/src/
├── views/
│   ├── DashboardView.vue        # Show org context
│   ├── DocumentDetailView.vue   # Add visibility controls
│   └── SearchView.vue           # Filter by org
├── stores/
│   ├── auth-store.ts            # Add org membership
│   └── document-store.ts        # Add org filtering
└── router/
    └── index.ts                 # Add org routes
```

---

## Migration Strategy

### Pre-Migration
1. **Backup database** (full dump)
2. **Test migration in staging** with production data copy
3. **Prepare rollback scripts**
4. **Notify users** of upcoming maintenance window

### Migration Execution
1. **Enable maintenance mode** (optional, for zero downtime)
2. **Run database migration** (schema changes)
3. **Run data migration** (create default orgs for existing users)
4. **Update application code** (deploy new version)
5. **Enable RLS policies**
6. **Verify data integrity**
7. **Disable maintenance mode**

### Post-Migration
1. **Monitor error logs** for RLS policy violations
2. **Test tenant isolation** with multiple test accounts
3. **Verify all existing documents** accessible to owners
4. **Check performance metrics**

---

## Testing Strategy

### Unit Tests
- Permission service logic
- Quota service calculations
- Invitation token generation/validation
- Document access resolution algorithm

### Integration Tests
- Organization CRUD operations
- Member invitation flow
- Group management
- Document access control
- RLS policy enforcement

### E2E Tests
- User creates organization
- User invites member via email
- Member accepts invitation
- Member uploads document
- Document visibility controls work
- Quota limits enforced

### Security Tests
- Cross-tenant data access attempts
- Token reuse attacks
- Quota bypass attempts
- SQL injection on org-related endpoints
- Permission escalation attempts

---

## Performance Targets

### Response Times
- Organization creation: < 500ms
- Member invitation: < 2s (email send included)
- Document upload: < 5s (unchanged)
- Search query: < 1s (unchanged)
- Organization switch: < 500ms

### Scalability
- Support 1000 organizations
- 100 members per organization
- 10,000 documents per organization
- 10 concurrent invitation sends

---

## Monitoring & Observability

### Metrics to Track
- Organization creation rate
- Invitation acceptance rate
- Document access denials (RLS)
- Quota limit hits
- Email delivery success rate

### Logging
- All organization mutations
- All permission changes
- All invitation events
- RLS policy violations (warnings)
- Quota warnings

### Alerts
- RLS policy failures
- Email delivery failures
- Quota exceeded events
- Performance degradation

---

## Rollout Plan

### Staging (Week 5, Day 1-2)
1. Deploy to staging environment
2. Run full test suite
3. Security testing
4. Performance testing
5. UAT with team members

### Production (Week 5, Day 3-5)
1. **Canary release** (10% of users)
   - Monitor for 24 hours
   - Check error rates
   - Verify data isolation

2. **Gradual rollout** (25% → 50% → 100%)
   - 25% for 24 hours
   - 50% for 24 hours
   - 100% full rollout

3. **Post-rollout monitoring**
   - Watch error logs
   - Monitor performance
   - Collect user feedback

---

## Documentation Updates

### Required Updates
- [ ] API documentation (new endpoints)
- [ ] Database schema documentation
- [ ] User guide (organization management)
- [ ] Admin guide (organization settings)
- [ ] Security documentation (RLS policies)

### New Documentation
- [ ] Organization setup guide
- [ ] Member invitation flow
- [ ] Document visibility guide
- [ ] Group management guide
- [ ] Quota management guide

---

## Support & Training

### Internal Team Training
- Multi-tenancy architecture overview
- RLS policy debugging
- Organization management workflows
- Common user issues

### User Communication
- Feature announcement email
- In-app tutorial for organization creation
- Help documentation for invitation flow
- FAQ for document visibility

---

## Success Metrics

### Technical Metrics
- Zero tenant data leakage incidents
- < 5% performance regression
- 100% test coverage on permission logic
- All API endpoints have permission checks

### Business Metrics
- 80% of users create organization within first week
- 50% of organizations have 2+ members
- 90% invitation acceptance rate
- < 5% quota limit hits

---

## Next Steps

1. **Review & approve plan** (User)
2. **Set up project board** (PM)
3. **Begin Phase 1** (Backend team)
4. **Schedule weekly check-ins** (Team)
5. **Prepare staging environment** (DevOps)

---

## Open Questions

1. **Email provider selection:** SendGrid vs Mailgun vs AWS SES?
   - **Recommendation:** SendGrid (free tier: 100 emails/day)

2. **Organization slug uniqueness:** Global or per-user?
   - **Recommendation:** Global uniqueness (first-come, first-served)

3. **Default organization naming:** User email or custom?
   - **Recommendation:** "{User's email}'s Workspace"

4. **Quota enforcement timing:** Pre-upload or post-upload?
   - **Recommendation:** Pre-upload (check before allowing upload)

5. **RLS policy scope:** Documents only or all tenant tables?
   - **Recommendation:** Start with documents, expand to all tables

---

## Related Resources

- [Brainstorm Report](../reports/brainstorm-260327-1209-multi-tenancy-architecture.md)
- [System Architecture](../../docs/system-architecture.md)
- [Database Schema](../../docs/database-schema.md)
- [API Documentation](../../docs/api-documentation.md)
