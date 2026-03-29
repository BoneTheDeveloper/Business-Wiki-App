# Multi-Tenancy Architecture Brainstorm Report

**Date:** 2026-03-27
**Project:** RAG Business Document Wiki
**Topic:** Multi-tenancy with organization-based document storage

---

## Problem Statement

**Current State:**
- Single-tenant architecture: Each user has isolated document storage
- Users cannot share documents or collaborate
- No organization/team concept
- No permission management beyond basic RBAC

**Requirements:**
1. Users create organizations (workspaces)
2. Invite team members with role-based permissions
3. Document visibility: Public (org-wide) / Restricted (group-based) / Private
4. Flexible group system for access control
5. Email invitations with secure tokens
6. Configurable quotas per organization

---

## Final Agreed Solution

### Architecture Model

**Tenant Isolation:** Shared Database with Logical Separation
- **Approach:** Add `organization_id` column to all tenant-scoped tables
- **Security:** PostgreSQL Row-Level Security (RLS) + Application-level checks
- **Rationale:** Cost-effective, simpler maintenance, proven pattern for SMBs

**Membership Model:** Single Organization per User
- **Approach:** User belongs to one org only (can be changed by admin)
- **Rationale:** Simpler data model, clearer ownership, adequate for dedicated teams

---

## Database Schema Design

### Core Tables

```sql
-- Organizations (tenants)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,  -- URL-friendly identifier
    owner_id UUID REFERENCES users(id) ON DELETE RESTRICT,

    -- Quota settings
    max_documents INTEGER DEFAULT 100,
    max_storage_bytes BIGINT DEFAULT 5368709120,  -- 5GB

    -- Current usage (denormalized for performance)
    current_documents INTEGER DEFAULT 0,
    current_storage_bytes BIGINT DEFAULT 0,

    -- Settings
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_organizations_slug ON organizations(slug);
CREATE INDEX ix_organizations_owner_id ON organizations(owner_id);

-- Organization members with roles
CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'owner', 'admin', 'member', 'viewer'

    -- Membership metadata
    invited_by_id UUID REFERENCES users(id),
    joined_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(organization_id, user_id)
);

CREATE INDEX ix_org_members_org_id ON organization_members(organization_id);
CREATE INDEX ix_org_members_user_id ON organization_members(user_id);

-- Groups for document access control
CREATE TABLE groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,

    created_by_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(organization_id, name)
);

CREATE INDEX ix_groups_org_id ON groups(organization_id);

-- Group membership
CREATE TABLE group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID REFERENCES groups(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    added_by_id UUID REFERENCES users(id),
    added_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(group_id, user_id)
);

CREATE INDEX ix_group_members_group_id ON group_members(group_id);
CREATE INDEX ix_group_members_user_id ON group_members(user_id);

-- Document access control
CREATE TABLE document_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,

    -- Access grantee (one of these must be set)
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    group_id UUID REFERENCES groups(id) ON DELETE CASCADE,

    -- Access level
    access_level VARCHAR(20) NOT NULL,  -- 'view', 'edit'

    granted_by_id UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),

    -- Ensure either user_id or group_id is set, not both
    CHECK (
        (user_id IS NOT NULL AND group_id IS NULL) OR
        (user_id IS NULL AND group_id IS NOT NULL)
    )
);

CREATE INDEX ix_doc_access_document_id ON document_access(document_id);
CREATE INDEX ix_doc_access_user_id ON document_access(user_id);
CREATE INDEX ix_doc_access_group_id ON document_access(group_id);

-- Email invitations
CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,

    -- Invite details
    invitee_email VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'admin', 'member', 'viewer'

    -- Security
    token_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256
    token_salt VARCHAR(64) NOT NULL,

    -- Tracking
    invited_by_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    used BOOLEAN DEFAULT FALSE
);

CREATE INDEX ix_invitations_token_hash ON invitations(token_hash);
CREATE INDEX ix_invitations_email ON invitations(invitee_email);
CREATE INDEX ix_invitations_org_id ON invitations(organization_id);

-- Modify existing documents table
ALTER TABLE documents ADD COLUMN organization_id UUID REFERENCES organizations(id);
ALTER TABLE documents ADD COLUMN visibility VARCHAR(20) DEFAULT 'private';  -- 'public', 'restricted', 'private'

CREATE INDEX ix_documents_org_id ON documents(organization_id);
CREATE INDEX ix_documents_visibility ON documents(visibility);
```

---

## Role Hierarchy & Permissions

### Role Definitions

```
Owner (1 per org)
  └─ Full control over org
  └─ Manage all members
  └─ Delete organization
  └─ Configure quotas

Admin (multiple)
  └─ Invite members
  └─ Manage groups
  └─ View all documents
  └─ Delete any document

Member (default)
  └─ Upload documents
  └─ Edit own documents
  └─ View public/restricted docs (if in group)
  └─ Create groups

Viewer
  └─ View public documents only
  └─ No upload/edit permissions
```

### Permission Matrix

| Action | Owner | Admin | Member | Viewer |
|--------|-------|-------|--------|--------|
| **Organization** |
| Delete org | ✓ | ✗ | ✗ | ✗ |
| Update settings | ✓ | ✗ | ✗ | ✗ |
| **Members** |
| Invite members | ✓ | ✓ | ✗ | ✗ |
| Remove members | ✓ | ✓ | ✗ | ✗ |
| Change roles | ✓ | ✓* | ✗ | ✗ |
| **Groups** |
| Create groups | ✓ | ✓ | ✓ | ✗ |
| Manage groups | ✓ | ✓ | Own only | ✗ |
| **Documents** |
| Upload documents | ✓ | ✓ | ✓ | ✗ |
| Edit own documents | ✓ | ✓ | ✓ | ✗ |
| Delete own documents | ✓ | ✓ | ✓ | ✗ |
| View all documents | ✓ | ✓ | ✗ | ✗ |
| Delete any document | ✓ | ✓ | ✗ | ✗ |
| View public docs | ✓ | ✓ | ✓ | ✓ |
| View restricted docs | ✓ | ✓ | If in group | ✗ |

*Admins cannot change Owner role

---

## Document Visibility Model

### Three-Tier Visibility

**1. Public (Organization-wide)**
- All org members can view
- Only owner/creator can edit
- Use case: Company policies, shared resources

**2. Restricted (Group-based)**
- Only tagged groups/members can access
- Granular permissions (view/edit)
- Use case: Department-specific docs, confidential projects

**3. Private**
- Only uploader + org admins/owner
- Maximum privacy
- Use case: Personal notes, sensitive data

### Access Resolution Algorithm

```python
async def can_access_document(
    user: User,
    document: Document,
    required_level: str = "view"
) -> bool:
    """
    Check if user can access document.

    Priority: Owner/Admin > Document Owner > Access List > Visibility
    """
    # 1. Org owner always has access
    org = await get_organization(document.organization_id)
    if user.id == org.owner_id:
        return True

    # 2. Org admin always has access
    member = await get_org_member(org.id, user.id)
    if member and member.role == "admin":
        return True

    # 3. Document owner always has access
    if document.user_id == user.id:
        return True

    # 4. Check visibility rules
    if document.visibility == "public":
        # All org members can view
        if required_level == "view":
            return member is not None
        # Only owner can edit public docs
        return False

    elif document.visibility == "restricted":
        # Check explicit access grants
        access = await get_document_access(document.id, user.id)
        if access:
            if required_level == "view":
                return True
            return access.access_level == "edit"

        # Check group-based access
        user_groups = await get_user_groups(user.id)
        for group in user_groups:
            access = await get_document_access(document.id, group_id=group.id)
            if access:
                if required_level == "view":
                    return True
                return access.access_level == "edit"

        return False

    else:  # private
        # Only uploader + admins (checked above)
        return False
```

---

## Invitation Flow

### Email Invitation System

**Flow:**

```
1. Admin/Owner initiates invite
   ↓
2. Generate secure token (SHA-256 + salt)
   ↓
3. Send email with invite link
   ↓
4. User clicks link → Accept/Decline
   ↓
5. If accept: Add to org_members with role
   ↓
6. Mark token as used
```

**Token Security:**
- One-time use (marked as `used` after acceptance)
- 7-day expiration (configurable)
- Per-token salt (prevents rainbow table attacks)
- Hash stored in DB (original token in URL only)

**Implementation:**

```python
# app/services/invitation_service.py
import secrets
import hashlib
from datetime import timedelta

class InvitationService:
    @staticmethod
    async def create_invitation(
        org_id: UUID,
        email: str,
        role: str,
        invited_by: User
    ) -> str:
        """Create secure invitation."""
        # Generate token
        random_bytes = secrets.token_bytes(32)
        salt = secrets.token_hex(32)
        token_hash = hashlib.sha256(
            random_bytes + salt.encode() + email.encode()
        ).hexdigest()

        # Store invitation
        invite = Invitation(
            organization_id=org_id,
            invitee_email=email,
            role=role,
            token_hash=token_hash,
            token_salt=salt,
            invited_by_id=invited_by.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(invite)
        await db.commit()

        # Return URL-safe token (not hash)
        return token_hash

    @staticmethod
    async def accept_invitation(token_hash: str, user: User) -> Organization:
        """Accept invitation and join organization."""
        invite = await db.execute(
            select(Invitation).where(
                Invitation.token_hash == token_hash,
                Invitation.expires_at > datetime.utcnow(),
                Invitation.used == False
            )
        )
        invite = invite.scalar_one_or_none()

        if not invite:
            raise ValueError("Invalid or expired invitation")

        # Add user to organization
        member = OrganizationMember(
            organization_id=invite.organization_id,
            user_id=user.id,
            role=invite.role,
            invited_by_id=invite.invited_by_id
        )
        db.add(member)

        # Mark invitation as used
        invite.used = True
        invite.used_at = datetime.utcnow()

        await db.commit()

        return await db.get(Organization, invite.organization_id)
```

---

## Quota Management

### Organization-Level Quotas

**Tracked Resources:**
- Document count (max 100 default)
- Storage size (max 5GB default)

**Enforcement:**

```python
# app/services/quota_service.py
class QuotaService:
    @staticmethod
    async def check_quota(org_id: UUID, file_size: int) -> dict:
        """Check if organization can upload document."""
        org = await db.get(Organization, org_id)

        # Check document count
        if org.current_documents >= org.max_documents:
            raise QuotaExceededError(
                f"Document limit reached ({org.max_documents})"
            )

        # Check storage
        if org.current_storage_bytes + file_size > org.max_storage_bytes:
            remaining = org.max_storage_bytes - org.current_storage_bytes
            raise QuotaExceededError(
                f"Storage limit reached. Remaining: {format_bytes(remaining)}"
            )

        return {
            "documents_remaining": org.max_documents - org.current_documents,
            "storage_remaining": org.max_storage_bytes - org.current_storage_bytes
        }

    @staticmethod
    async def increment_usage(org_id: UUID, file_size: int):
        """Increment usage counters."""
        await db.execute(
            update(Organization)
            .where(Organization.id == org_id)
            .values(
                current_documents=Organization.current_documents + 1,
                current_storage_bytes=Organization.current_storage_bytes + file_size
            )
        )
        await db.commit()

    @staticmethod
    async def decrement_usage(org_id: UUID, file_size: int):
        """Decrement usage counters (on deletion)."""
        await db.execute(
            update(Organization)
            .where(Organization.id == org_id)
            .values(
                current_documents=Organization.current_documents - 1,
                current_storage_bytes=Organization.current_storage_bytes - file_size
            )
        )
        await db.commit()
```

---

## Row-Level Security (RLS) Implementation

### PostgreSQL RLS Policies

```sql
-- Enable RLS on documents
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policy 1: Org members can see documents in their org
CREATE POLICY org_member_document_access ON documents
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM organization_members om
            WHERE om.organization_id = documents.organization_id
            AND om.user_id = current_setting('app.current_user_id')::uuid
        )
        AND (
            -- Public documents
            documents.visibility = 'public'
            OR
            -- Restricted documents with access grant
            (documents.visibility = 'restricted' AND EXISTS (
                SELECT 1 FROM document_access da
                WHERE da.document_id = documents.id
                AND (
                    da.user_id = current_setting('app.current_user_id')::uuid
                    OR da.group_id IN (
                        SELECT gm.group_id FROM group_members gm
                        WHERE gm.user_id = current_setting('app.current_user_id')::uuid
                    )
                )
            ))
            OR
            -- Private documents (owner or admin)
            (documents.visibility = 'private' AND (
                documents.user_id = current_setting('app.current_user_id')::uuid
                OR EXISTS (
                    SELECT 1 FROM organization_members om
                    WHERE om.organization_id = documents.organization_id
                    AND om.user_id = current_setting('app.current_user_id')::uuid
                    AND om.role IN ('owner', 'admin')
                )
            ))
        )
    );

-- Policy 2: Only document owner can update/delete
CREATE POLICY document_owner_modify ON documents
    FOR UPDATE, DELETE
    USING (
        documents.user_id = current_setting('app.current_user_id')::uuid
        OR EXISTS (
            SELECT 1 FROM organization_members om
            WHERE om.organization_id = documents.organization_id
            AND om.user_id = current_setting('app.current_user_id')::uuid
            AND om.role IN ('owner', 'admin')
        )
    );
```

### Application-Level RLS Context

```python
# app/api/deps.py
async def get_current_user_with_rls(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Set RLS context for current user."""
    await db.execute(
        text("SET LOCAL app.current_user_id = :user_id"),
        {"user_id": str(current_user.id)}
    )
    return current_user
```

---

## API Endpoints

### Organization Management

```python
# POST /api/v1/organizations
# Create organization
{
    "name": "Acme Corp",
    "slug": "acme-corp"
}

# GET /api/v1/organizations/{org_id}
# Get organization details

# POST /api/v1/organizations/{org_id}/invite
# Invite member
{
    "email": "user@example.com",
    "role": "member"
}

# POST /api/v1/invitations/{token}/accept
# Accept invitation

# GET /api/v1/organizations/{org_id}/members
# List organization members

# DELETE /api/v1/organizations/{org_id}/members/{user_id}
# Remove member
```

### Group Management

```python
# POST /api/v1/organizations/{org_id}/groups
# Create group
{
    "name": "Engineering",
    "description": "Engineering team"
}

# POST /api/v1/groups/{group_id}/members
# Add member to group
{
    "user_id": "uuid"
}

# GET /api/v1/organizations/{org_id}/groups
# List groups
```

### Document Access Control

```python
# POST /api/v1/documents/{doc_id}/access
# Grant document access
{
    "user_id": "uuid",  # or group_id
    "access_level": "view"
}

# DELETE /api/v1/documents/{doc_id}/access/{access_id}
# Revoke access

# PUT /api/v1/documents/{doc_id}
# Update document visibility
{
    "visibility": "restricted"
}
```

---

## Frontend Changes

### New Components

**Organization Management:**
- `OrganizationDashboard.vue` - Org overview, stats, settings
- `OrganizationMembers.vue` - Member list, invite UI, role management
- `OrganizationGroups.vue` - Group management interface

**Invitation Flow:**
- `AcceptInvitation.vue` - Handle invitation acceptance
- `InviteMemberDialog.vue` - Invite form with email input

**Document Access:**
- `DocumentAccessManager.vue` - Manage document permissions
- `VisibilitySelector.vue` - Public/Restricted/Private toggle
- `GroupSelector.vue` - Multi-select groups for restricted docs

### Store Updates

```typescript
// stores/organization-store.ts
export const useOrganizationStore = defineStore('organization', {
  state: () => ({
    currentOrg: null as Organization | null,
    members: [] as Member[],
    groups: [] as Group[],
    invitations: [] as Invitation[]
  }),

  actions: {
    async fetchOrganization(orgId: string) {
      // GET /organizations/{org_id}
    },

    async inviteMember(email: string, role: string) {
      // POST /organizations/{org_id}/invite
    },

    async createGroup(name: string, description: string) {
      // POST /organizations/{org_id}/groups
    }
  }
})
```

---

## Migration Strategy

### Phase 1: Add Organization Tables (Week 1)

**Tasks:**
1. Create new tables (organizations, organization_members, groups, etc.)
2. Add `organization_id` to documents table
3. Create default organization for each existing user
4. Migrate existing documents to default orgs

**Migration Script:**

```python
# migrations/add_multi_tenancy.py
async def migrate_to_multi_tenant():
    """Migrate existing users to default organizations."""

    # Create default org for each user
    users = await db.execute(select(User))
    for user in users.scalars():
        org = Organization(
            name=f"{user.email}'s Workspace",
            slug=f"user-{user.id[:8]}",
            owner_id=user.id
        )
        db.add(org)
        await db.flush()

        # Add user as owner
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role="owner"
        )
        db.add(member)

        # Update user's documents
        await db.execute(
            update(Document)
            .where(Document.user_id == user.id)
            .values(organization_id=org.id, visibility="private")
        )

    await db.commit()
```

### Phase 2: Implement Core Features (Week 2-3)

**Tasks:**
1. Implement invitation system
2. Add group management
3. Implement document access control
4. Enable RLS on documents table
5. Update API endpoints with org context

### Phase 3: Frontend Updates (Week 4)

**Tasks:**
1. Create organization management UI
2. Implement invitation flow UI
3. Add document visibility controls
4. Update document list to respect permissions
5. Add group management interface

### Phase 4: Testing & Rollout (Week 5)

**Tasks:**
1. Unit tests for permission logic
2. Integration tests for RLS
3. E2E tests for invitation flow
4. Security audit (tenant isolation)
5. Performance testing
6. Staging deployment
7. Production rollout

---

## Performance Considerations

### Database Indexing

**Critical Indexes:**
```sql
-- Organization membership
CREATE INDEX ix_org_members_composite ON organization_members(organization_id, user_id);

-- Document access
CREATE INDEX ix_doc_access_composite ON document_access(document_id, user_id, group_id);

-- Group membership
CREATE INDEX ix_group_members_composite ON group_members(group_id, user_id);

-- Documents by org
CREATE INDEX ix_documents_org_visibility ON documents(organization_id, visibility);
```

### Caching Strategy

**Redis Cache Keys:**
- `org:{org_id}:members` - List of org members (5 min TTL)
- `org:{org_id}:groups` - List of groups (5 min TTL)
- `user:{user_id}:orgs` - User's organizations (10 min TTL)
- `doc:{doc_id}:access` - Document access list (10 min TTL)

**Cache Invalidation:**
- On member add/remove: Invalidate `org:{org_id}:members`
- On group add/remove: Invalidate `org:{org_id}:groups`
- On document access change: Invalidate `doc:{doc_id}:access`

---

## Security Checklist

### Critical Security Measures

- [ ] **RLS Enabled:** All tenant-scoped tables have RLS policies
- [ ] **Token Security:** One-time use, salted, hashed, expiring tokens
- [ ] **Permission Checks:** Every API endpoint validates permissions
- [ ] **Tenant Isolation:** Test with multiple users accessing each other's data
- [ ] **Quota Validation:** Server-side checks (no client-side trust)
- [ ] **SQL Injection Prevention:** Parameterized queries only
- [ ] **Rate Limiting:** Invitation endpoints rate-limited
- [ ] **Audit Logging:** Log all permission changes and invitations

### Security Testing

```python
# tests/security/test_tenant_isolation.py
async def test_user_cannot_access_other_org_documents():
    """Verify RLS prevents cross-tenant access."""
    user1 = await create_user()
    user2 = await create_user()

    org1 = await create_organization(user1)
    org2 = await create_organization(user2)

    doc1 = await create_document(org1, user1)

    # Try to access with user2
    with pytest.raises(HTTPException) as exc:
        await get_document(doc1.id, user2)

    assert exc.value.status_code == 403
```

---

## Risk Assessment

### High-Risk Areas

**1. Data Leakage**
- **Risk:** Users access documents from other orgs
- **Mitigation:** RLS + application checks + comprehensive testing
- **Contingency:** Disable RLS temporarily if critical issue found

**2. Token Theft**
- **Risk:** Invitation tokens stolen and reused
- **Mitigation:** One-time use, short expiration, secure hashing
- **Contingency:** Invalidate all tokens for org if breach detected

**3. Performance Regression**
- **Risk:** RLS adds query overhead
- **Mitigation:** Proper indexing, query optimization
- **Contingency:** Disable RLS, rely on application-level checks

### Medium-Risk Areas

**4. Quota Bypass**
- **Risk:** Users exceed limits through race conditions
- **Mitigation:** Database-level constraints, atomic increments
- **Contingency:** Manual quota enforcement, user warnings

**5. Group Complexity**
- **Risk:** Complex permission logic leads to errors
- **Mitigation:** Thorough testing, clear documentation
- **Contingency:** Simplify to user-level access only

---

## Implementation Recommendations

### Priority 1 (Critical - MVP)

1. **Add organization tables** - Core multi-tenancy structure
2. **Implement RLS on documents** - Tenant isolation
3. **Email invitation system** - Member management
4. **Basic role system** - Owner/Admin/Member/Viewer
5. **Document visibility** - Public/Private support

### Priority 2 (Important - Phase 2)

6. **Group system** - Flexible access control
7. **Restricted visibility** - Group-based document access
8. **Quota management** - Resource tracking and limits
9. **Caching layer** - Performance optimization
10. **Audit logging** - Security compliance

### Priority 3 (Nice to Have - Phase 3)

11. **Advanced permissions** - Fine-grained ACLs
12. **Organization settings** - Branding, custom domains
13. **Team analytics** - Usage insights
14. **API keys** - Organization-level integrations

---

## Success Criteria

### MVP Acceptance Criteria

- [ ] Users can create organizations
- [ ] Owners can invite members via email
- [ ] Members can join organizations with assigned roles
- [ ] Documents are isolated per organization
- [ ] RLS prevents cross-tenant access
- [ ] Public/Private visibility works correctly
- [ ] Quota limits are enforced

### Performance Metrics

- Document upload: < 5 seconds (unchanged)
- Search query: < 1 second (unchanged)
- Organization switch: < 500ms
- Member list load: < 1 second
- Invitation send: < 2 seconds

### Quality Metrics

- Zero tenant data leakage incidents
- 100% test coverage on permission logic
- All RLS policies tested with multiple users
- Zero SQL injection vulnerabilities
- All API endpoints have permission checks

---

## Unresolved Questions

1. **Email Provider:** Should we use SendGrid, Mailgun, or custom SMTP?
   - **Recommendation:** SendGrid for reliability and templates

2. **Organization Deletion:** What happens to documents when org is deleted?
   - **Recommendation:** Soft delete with 30-day recovery period

3. **Organization Transfer:** Can ownership be transferred to another user?
   - **Recommendation:** Yes, with confirmation from both parties

4. **Multi-Org Support:** Will we support users in multiple orgs in future?
   - **Recommendation:** Design for it, implement single-org first

5. **Quota Tiers:** Should we implement paid tiers with different quotas?
   - **Recommendation:** Yes, track in `organizations.plan` field

---

## Next Steps

1. **User confirms approach:** Review this brainstorm report
2. **Create implementation plan:** Detailed technical plan with `/plan` skill
3. **Begin Phase 1:** Database schema migration
4. **Iterative development:** Follow phased approach
5. **Testing & rollout:** Comprehensive security testing

**Timeline Estimate:** 4-5 weeks for full implementation (MVP + Phase 2)
