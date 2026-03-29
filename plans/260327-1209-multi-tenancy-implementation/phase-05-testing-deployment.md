# Phase 5: Testing & Deployment

**Priority:** Critical
**Duration:** Week 5 (5 days)
**Status:** Pending
**Dependencies:** All previous phases

---

## Overview

Comprehensive testing, staging deployment, and production rollout of multi-tenancy features.

### Key Objectives
- Complete test coverage (unit, integration, E2E)
- Performance testing and optimization
- Staging deployment and UAT
- Production deployment with monitoring
- Documentation and training

---

## Requirements

### Testing Requirements
- Unit test coverage > 80%
- Integration tests for all API endpoints
- E2E tests for critical user flows
- Security tests pass 100%
- Performance benchmarks met

### Deployment Requirements
- Zero downtime deployment
- Rollback plan tested
- Monitoring alerts configured
- User communication sent

---

## Implementation Steps

### Step 1: Unit Tests (Day 1)

**File:** `backend/tests/unit/test_organization_service.py`

```python
"""Unit tests for organization service."""
import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.organization_service import OrganizationService
from app.services.permission_service import PermissionService
from app.models.models import User, Organization, OrganizationMember
from app.core.exceptions import (
    OrganizationNotFound,
    PermissionDenied,
    SlugAlreadyExists
)


@pytest.mark.asyncio
class TestOrganizationService:
    """Organization service unit tests."""

    async def test_create_organization_success(self, db_session, test_user):
        """Test successful organization creation."""
        org = await OrganizationService.create_organization(
            db_session,
            test_user,
            {"name": "Test Org", "slug": "test-org"}
        )

        assert org.id is not None
        assert org.name == "Test Org"
        assert org.slug == "test-org"
        assert org.owner_id == test_user.id
        assert org.max_documents == 100
        assert org.max_storage_bytes == 5368709120

        # Verify membership created
        member = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == test_user.id
            )
        )
        member = member.scalar_one_or_none()
        assert member is not None
        assert member.role == "owner"

    async def test_create_organization_duplicate_slug(self, db_session, test_user):
        """Test duplicate slug rejection."""
        # Create first org
        await OrganizationService.create_organization(
            db_session,
            test_user,
            {"name": "Org 1", "slug": "test-org"}
        )
        await db_session.commit()

        # Try duplicate slug
        with pytest.raises(SlugAlreadyExists):
            await OrganizationService.create_organization(
                db_session,
                test_user,
                {"name": "Org 2", "slug": "test-org"}
            )

    async def test_get_organization_success(self, db_session, test_user, test_org):
        """Test organization retrieval."""
        org = await OrganizationService.get_organization(
            db_session,
            test_org.id,
            test_user.id
        )

        assert org.id == test_org.id
        assert org.name == test_org.name

    async def test_get_organization_not_member(self, db_session, test_org):
        """Test access denied for non-members."""
        other_user = User(
            email="other@test.com",
            password_hash="hash",
            role="user"
        )
        db_session.add(other_user)
        await db_session.commit()

        with pytest.raises(PermissionDenied):
            await OrganizationService.get_organization(
                db_session,
                test_org.id,
                other_user.id
            )

    async def test_update_organization_owner_only(self, db_session, test_org):
        """Test only owner can update organization."""
        # Create member
        member_user = User(
            email="member@test.com",
            password_hash="hash",
            role="user"
        )
        db_session.add(member_user)
        await db_session.commit()

        membership = OrganizationMember(
            organization_id=test_org.id,
            user_id=member_user.id,
            role="admin"
        )
        db_session.add(membership)
        await db_session.commit()

        # Admin tries to update
        with pytest.raises(PermissionDenied):
            await OrganizationService.update_organization(
                db_session,
                test_org.id,
                member_user.id,
                {"name": "Hacked Org"}
            )

    async def test_delete_organization_soft_delete(self, db_session, test_user, test_org):
        """Test soft delete of organization."""
        await OrganizationService.delete_organization(
            db_session,
            test_org.id,
            test_user.id
        )
        await db_session.commit()

        # Verify soft deleted
        org = await db_session.get(Organization, test_org.id)
        assert org.is_active is False

    async def test_get_organization_stats(self, db_session, test_org, test_user):
        """Test organization statistics."""
        # Upload some documents
        for i in range(3):
            doc = Document(
                user_id=test_user.id,
                organization_id=test_org.id,
                filename=f"doc{i}.pdf",
                file_path=f"/docs/doc{i}.pdf",
                file_size=1024 * (i + 1)
            )
            db_session.add(doc)
        await db_session.commit()

        stats = await OrganizationService.get_organization_stats(
            db_session,
            test_org.id
        )

        assert stats["document_count"] == 3
        assert stats["storage_bytes"] == 1024 * (1 + 2 + 3)


@pytest.mark.asyncio
class TestPermissionService:
    """Permission service unit tests."""

    async def test_get_user_role(self, db_session, test_org, test_user):
        """Test role retrieval."""
        role = await PermissionService.get_user_role(
            db_session,
            test_org.id,
            test_user.id
        )
        assert role == "owner"

    async def test_check_organization_permission(self, db_session, test_org, test_user):
        """Test permission check."""
        has_permission = await PermissionService.check_organization_permission(
            db_session,
            test_org.id,
            test_user.id,
            ["owner", "admin"]
        )
        assert has_permission is True

    async def test_can_access_document_public(self, db_session, test_org, test_user):
        """Test public document access."""
        # Create viewer
        viewer = User(email="viewer@test.com", password_hash="hash", role="user")
        db_session.add(viewer)
        await db_session.commit()

        membership = OrganizationMember(
            organization_id=test_org.id,
            user_id=viewer.id,
            role="viewer"
        )
        db_session.add(membership)
        await db_session.commit()

        # Create public document
        doc = Document(
            user_id=test_user.id,
            organization_id=test_org.id,
            filename="public.pdf",
            file_path="/docs/public.pdf",
            visibility="public"
        )
        db_session.add(doc)
        await db_session.commit()

        # Viewer should have view access
        has_access = await PermissionService.can_access_document(
            db_session,
            doc,
            viewer.id,
            "view"
        )
        assert has_access is True

        # Viewer should NOT have edit access
        has_edit = await PermissionService.can_access_document(
            db_session,
            doc,
            viewer.id,
            "edit"
        )
        assert has_edit is False

    async def test_can_access_document_restricted_with_group(
        self, db_session, test_org, test_user
    ):
        """Test restricted document with group access."""
        # Create member
        member = User(email="member@test.com", password_hash="hash", role="user")
        db_session.add(member)
        await db_session.commit()

        membership = OrganizationMember(
            organization_id=test_org.id,
            user_id=member.id,
            role="member"
        )
        db_session.add(membership)

        # Create group
        group = Group(
            organization_id=test_org.id,
            name="Engineering",
            created_by_id=test_user.id
        )
        db_session.add(group)
        await db_session.commit()

        # Add member to group
        group_member = GroupMember(
            group_id=group.id,
            user_id=member.id
        )
        db_session.add(group_member)
        await db_session.commit()

        # Create restricted document
        doc = Document(
            user_id=test_user.id,
            organization_id=test_org.id,
            filename="restricted.pdf",
            file_path="/docs/restricted.pdf",
            visibility="restricted"
        )
        db_session.add(doc)
        await db_session.commit()

        # Grant group access
        access = DocumentAccess(
            document_id=doc.id,
            group_id=group.id,
            access_level="view"
        )
        db_session.add(access)
        await db_session.commit()

        # Member should have access
        has_access = await PermissionService.can_access_document(
            db_session,
            doc,
            member.id,
            "view"
        )
        assert has_access is True
```

---

### Step 2: Integration Tests (Day 2)

**File:** `backend/tests/integration/test_organization_api.py`

```python
"""Integration tests for organization API."""
import pytest
from httpx import AsyncClient
from uuid import UUID

from app.models.models import User, Organization


@pytest.mark.asyncio
class TestOrganizationAPI:
    """Organization API integration tests."""

    async def test_create_organization(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test organization creation via API."""
        response = await client.post(
            "/api/v1/organizations",
            json={
                "name": "Test Organization",
                "slug": "test-org-api"
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Test Organization"
        assert data["slug"] == "test-org-api"
        assert "id" in data
        assert data["max_documents"] == 100
        assert data["max_storage_bytes"] == 5368709120

    async def test_create_organization_invalid_slug(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test invalid slug validation."""
        response = await client.post(
            "/api/v1/organizations",
            json={
                "name": "Test Org",
                "slug": "Invalid Slug!"  # Invalid characters
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    async def test_list_organizations(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test listing user's organizations."""
        response = await client.get(
            "/api/v1/organizations",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1
        assert any(org["id"] == str(test_org.id) for org in data)

    async def test_get_organization(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test getting organization details."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(test_org.id)
        assert data["name"] == test_org.name

    async def test_get_organization_unauthorized(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test accessing organization without membership."""
        # Create org owned by different user
        other_org = Organization(
            name="Other Org",
            slug="other-org",
            owner_id=UUID("00000000-0000-0000-0000-000000000001")
        )
        # ... save to DB

        response = await client.get(
            f"/api/v1/organizations/{other_org.id}",
            headers=auth_headers
        )

        assert response.status_code == 403

    async def test_invite_member(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test inviting member to organization."""
        response = await client.post(
            f"/api/v1/organizations/{test_org.id}/invite",
            json={
                "email": "newmember@test.com",
                "role": "member"
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()

        assert data["invitee_email"] == "newmember@test.com"
        assert data["role"] == "member"
        assert "id" in data

    async def test_invite_member_permission_denied(
        self, client: AsyncClient, test_org, test_user
    ):
        """Test member cannot invite."""
        # Create member user
        member = User(email="member@test.com", password_hash="hash", role="user")
        # ... save and create membership with "member" role

        member_headers = get_auth_headers(member.id)

        response = await client.post(
            f"/api/v1/organizations/{test_org.id}/invite",
            json={
                "email": "another@test.com",
                "role": "member"
            },
            headers=member_headers
        )

        assert response.status_code == 403

    async def test_accept_invitation(
        self, client: AsyncClient, test_org, test_user, db_session
    ):
        """Test accepting invitation."""
        # Create invitation
        invitation = Invitation(
            organization_id=test_org.id,
            invitee_email="invited@test.com",
            role="member",
            token_hash="test_token_hash",
            token_salt="test_salt",
            invited_by_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db_session.add(invitation)
        await db_session.commit()

        # Create user with matching email
        invited_user = User(
            email="invited@test.com",
            password_hash="hash",
            role="user"
        )
        db_session.add(invited_user)
        await db_session.commit()

        invited_headers = get_auth_headers(invited_user.id)

        response = await client.post(
            f"/api/v1/invitations/{invitation.token_hash}/accept",
            headers=invited_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(test_org.id)

        # Verify membership created
        membership = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == test_org.id,
                OrganizationMember.user_id == invited_user.id
            )
        )
        assert membership.scalar_one_or_none() is not None

    async def test_document_visibility_update(
        self, client: AsyncClient, auth_headers: dict, test_org, test_document
    ):
        """Test updating document visibility."""
        response = await client.patch(
            f"/api/v1/documents/{test_document.id}/visibility",
            params={"visibility": "public"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["visibility"] == "public"

    async def test_grant_document_access(
        self, client: AsyncClient, auth_headers: dict, test_org, test_document, test_user
    ):
        """Test granting document access."""
        # Create another user
        other_user = User(email="other@test.com", password_hash="hash", role="user")
        # ... save and create membership

        response = await client.post(
            f"/api/v1/documents/{test_document.id}/access",
            json={
                "user_id": str(other_user.id),
                "access_level": "view"
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()

        assert data["user_id"] == str(other_user.id)
        assert data["access_level"] == "view"
```

---

### Step 3: E2E Tests (Day 2)

**File:** `frontend/tests/e2e/organization.spec.ts`

```typescript
import { test, expect } from '@playwright/test'

test.describe('Organization Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.fill('input[type="email"]', 'test@test.com')
    await page.fill('input[type="password"]', 'password123')
    await page.click('button[type="submit"]')
    await page.waitForURL('/dashboard')
  })

  test('should create organization', async ({ page }) => {
    await page.goto('/organizations/create')

    await page.fill('input[name="name"]', 'My Test Organization')
    await page.fill('input[name="slug"]', 'my-test-org')
    await page.click('button[type="submit"]')

    // Should redirect to org dashboard
    await page.waitForURL(/\/organizations\/[a-f0-9-]+/)
    await expect(page.locator('h1')).toContainText('My Test Organization')
  })

  test('should invite member', async ({ page }) => {
    // Navigate to org dashboard
    await page.goto('/organizations')
    await page.click('text=Test Organization')

    // Click invite button
    await page.click('button:has-text("Invite Member")')

    // Fill invitation form
    await page.fill('input[name="email"]', 'newmember@example.com')
    await page.selectOption('select[name="role"]', 'member')
    await page.click('button:has-text("Send Invitation")')

    // Check success message
    await expect(page.locator('.p-toast-success')).toBeVisible()
  })

  test('should accept invitation', async ({ page, context }) => {
    // Simulate receiving invitation email with token
    const inviteToken = 'test-invite-token-123'

    // Navigate to accept invitation page
    await page.goto(`/invitations/${inviteToken}/accept`)

    // Should show organization details
    await expect(page.locator('text=Join Test Organization')).toBeVisible()
    await page.click('button:has-text("Accept Invitation")')

    // Should redirect to org dashboard
    await page.waitForURL(/\/organizations\/[a-f0-9-]+/)
    await expect(page.locator('h1')).toContainText('Test Organization')
  })

  test('should create group', async ({ page }) => {
    await page.goto('/organizations')
    await page.click('text=Test Organization')

    // Navigate to groups tab
    await page.click('text=Groups')
    await page.click('button:has-text("Create Group")')

    await page.fill('input[name="name"]', 'Engineering Team')
    await page.fill('textarea[name="description"]', 'Engineering department')
    await page.click('button[type="submit"]')

    await expect(page.locator('text=Engineering Team')).toBeVisible()
  })

  test('should set document visibility', async ({ page }) => {
    // Upload document
    await page.goto('/documents/upload')
    await page.setInputFiles('input[type="file"]', 'test.pdf')
    await page.fill('input[name="filename"]', 'Test Document')

    // Set visibility to restricted
    await page.click('text=Restricted')
    await page.click('text=Users')
    await page.click('.user-selector')
    await page.click('text=john@example.com')

    await page.click('button:has-text("Upload")')

    // Verify visibility
    await page.waitForURL(/\/documents\/[a-f0-9-]+/)
    await expect(page.locator('.visibility-badge')).toContainText('Restricted')
  })

  test('should switch organizations', async ({ page }) => {
    await page.goto('/dashboard')

    // Open org switcher
    await page.click('.organization-switcher')
    await page.click('text=Other Organization')

    // Should update context
    await expect(page.locator('.current-org-name')).toContainText('Other Organization')
  })

  test('should prevent cross-tenant access', async ({ page }) => {
    // Try to access document from different org
    const otherOrgDocId = '00000000-0000-0000-0000-000000000001'

    const response = await page.goto(`/documents/${otherOrgDocId}`)

    // Should get 403 or redirect
    expect(response?.status()).toBe(403)
  })
})

test.describe('Permission-based UI', () => {
  test('viewer cannot see upload button', async ({ page }) => {
    // Login as viewer
    await loginAs(page, 'viewer@test.com', 'password')

    await page.goto('/dashboard')

    // Upload button should not be visible
    await expect(page.locator('button:has-text("Upload")')).not.toBeVisible()
  })

  test('member cannot see invite button', async ({ page }) => {
    // Login as member
    await loginAs(page, 'member@test.com', 'password')

    await page.goto('/organizations')
    await page.click('text=Test Organization')

    // Invite button should not be visible
    await expect(page.locator('button:has-text("Invite Member")')).not.toBeVisible()
  })

  test('admin can see all members', async ({ page }) => {
    // Login as admin
    await loginAs(page, 'admin@test.com', 'password')

    await page.goto('/organizations')
    await page.click('text=Test Organization')
    await page.click('text=Members')

    // Should see member list
    await expect(page.locator('.member-list')).toBeVisible()
    await expect(page.locator('.member-item')).toHaveCount(5)
  })
})
```

---

### Step 4: Performance Testing (Day 3)

**File:** `backend/tests/performance/test_rls_performance.py`

```python
"""Performance tests for RLS."""
import pytest
import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Document


@pytest.mark.asyncio
class TestRLSPerformance:
    """RLS performance benchmarks."""

    async def test_document_query_with_rls(self, db_session, test_user, test_org):
        """Test query performance with RLS enabled."""
        # Create 1000 documents
        for i in range(1000):
            doc = Document(
                user_id=test_user.id,
                organization_id=test_org.id,
                filename=f"doc{i}.pdf",
                file_path=f"/docs/doc{i}.pdf",
                visibility="public"
            )
            db_session.add(doc)

        await db_session.commit()

        # Set RLS context
        await db_session.execute(
            text("SET LOCAL app.current_user_id = :user_id"),
            {"user_id": str(test_user.id)}
        )

        # Measure query time
        start = time.time()

        result = await db_session.execute(
            select(Document)
            .where(Document.organization_id == test_org.id)
            .limit(100)
        )
        documents = result.scalars().all()

        elapsed = (time.time() - start) * 1000  # ms

        assert len(documents) == 100
        assert elapsed < 100, f"Query took {elapsed}ms (target: <100ms)"
        print(f"✅ RLS query time: {elapsed:.2f}ms for 100 docs")

    async def test_permission_check_performance(self, db_session, test_org):
        """Test permission check speed."""
        from app.services.permission_service import PermissionService

        # Create member
        member = User(email="member@test.com", password_hash="hash", role="user")
        db_session.add(member)
        await db_session.commit()

        membership = OrganizationMember(
            organization_id=test_org.id,
            user_id=member.id,
            role="member"
        )
        db_session.add(membership)
        await db_session.commit()

        # Create document
        doc = Document(
            user_id=test_user.id,
            organization_id=test_org.id,
            filename="test.pdf",
            file_path="/docs/test.pdf",
            visibility="public"
        )
        db_session.add(doc)
        await db_session.commit()

        # Measure permission check time
        start = time.time()

        for _ in range(100):
            has_access = await PermissionService.can_access_document(
                db_session,
                doc,
                member.id,
                "view"
            )

        elapsed = ((time.time() - start) * 1000) / 100  # Average per check

        assert elapsed < 10, f"Permission check took {elapsed}ms (target: <10ms)"
        print(f"✅ Permission check time: {elapsed:.2f}ms average")

    async def test_search_with_rls(self, db_session, test_user, test_org):
        """Test search performance with RLS."""
        # Create documents with chunks
        for i in range(100):
            doc = Document(
                user_id=test_user.id,
                organization_id=test_org.id,
                filename=f"doc{i}.pdf",
                file_path=f"/docs/doc{i}.pdf",
                visibility="public"
            )
            db_session.add(doc)
            await db_session.flush()

            # Add chunks
            for j in range(10):
                chunk = DocumentChunk(
                    document_id=doc.id,
                    content=f"Content {i}-{j}",
                    chunk_index=j
                )
                db_session.add(chunk)

        await db_session.commit()

        # Set RLS context
        await db_session.execute(
            text("SET LOCAL app.current_user_id = :user_id"),
            {"user_id": str(test_user.id)}
        )

        # Measure search time
        start = time.time()

        result = await db_session.execute(
            select(DocumentChunk)
            .join(Document)
            .where(Document.organization_id == test_org.id)
            .limit(10)
        )
        chunks = result.scalars().all()

        elapsed = (time.time() - start) * 1000

        assert len(chunks) == 10
        assert elapsed < 50, f"Search took {elapsed}ms (target: <50ms)"
        print(f"✅ Search with RLS: {elapsed:.2f}ms")
```

---

### Step 5: Staging Deployment (Day 4)

**File:** `deployment/staging-deploy.sh`

```bash
#!/bin/bash
# Staging deployment script

set -e

echo "🚀 Starting staging deployment..."

# 1. Backup database
echo "📦 Creating database backup..."
pg_dump -h $STAGING_DB_HOST -U $STAGING_DB_USER $STAGING_DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Pull latest code
echo "📥 Pulling latest code..."
git pull origin main

# 3. Run migrations
echo "🔄 Running database migrations..."
cd backend
poetry run alembic upgrade head

# 4. Run tests
echo "🧪 Running tests..."
poetry run pytest tests/ -v

if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Aborting deployment."
    exit 1
fi

# 5. Build frontend
echo "🏗️ Building frontend..."
cd ../frontend
npm run build

# 6. Deploy services
echo "🚢 Deploying services..."
docker-compose -f docker-compose.staging.yml pull
docker-compose -f docker-compose.staging.yml up -d --build

# 7. Health check
echo "🏥 Running health checks..."
sleep 10

curl -f https://staging.example.com/health || exit 1

# 8. Run smoke tests
echo "💨 Running smoke tests..."
cd ../backend
poetry run pytest tests/smoke/ -v

echo "✅ Staging deployment complete!"
```

---

### Step 6: Production Deployment (Day 5)

**File:** `deployment/production-deploy.sh`

```bash
#!/bin/bash
# Production deployment with canary release

set -e

CANARY_PERCENTAGE=${1:-10}

echo "🚀 Starting production deployment (canary: ${CANARY_PERCENTAGE}%)..."

# 1. Pre-deployment checks
echo "✅ Running pre-deployment checks..."

# Check all tests pass
cd backend
poetry run pytest tests/ -v
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Aborting."
    exit 1
fi

# Check security tests
poetry run pytest tests/security/ -v
if [ $? -ne 0 ]; then
    echo "❌ Security tests failed. Aborting."
    exit 1
fi

# 2. Database migration
echo "🔄 Running database migration..."

# Enable maintenance mode (optional)
# kubectl scale deployment backend --replicas=0

# Run migration
poetry run alembic upgrade head

# 3. Canary deployment
echo "🐦 Deploying canary (${CANARY_PERCENTAGE}%)..."

# Deploy to canary instances
kubectl apply -f k8s/canary-deployment.yaml

# Wait for canary to be ready
kubectl rollout status deployment/backend-canary

# 4. Monitor canary
echo "📊 Monitoring canary for 1 hour..."
sleep 3600

# Check error rates
ERROR_RATE=$(curl -s https://monitoring.example.com/api/error-rate?canary=true)
if [ $(echo "$ERROR_RATE > 1.0" | bc) -eq 1 ]; then
    echo "❌ Canary error rate too high: ${ERROR_RATE}%"
    echo "🔄 Rolling back..."
    kubectl rollout undo deployment/backend-canary
    exit 1
fi

# 5. Gradual rollout
for PERCENTAGE in 25 50 75 100; do
    echo "📈 Scaling to ${PERCENTAGE}%..."

    # Update traffic split
    kubectl patch service backend -p "{\"spec\":{\"canaryWeight\":${PERCENTAGE}}}"

    # Monitor for 30 minutes
    sleep 1800

    # Check metrics
    ERROR_RATE=$(curl -s https://monitoring.example.com/api/error-rate)
    if [ $(echo "$ERROR_RATE > 1.0" | bc) -eq 1 ]; then
        echo "❌ Error rate too high: ${ERROR_RATE}%"
        echo "🔄 Rolling back..."
        kubectl rollout undo deployment/backend
        exit 1
    fi
done

# 6. Post-deployment
echo "🎉 Deployment complete!"

# Send notification
curl -X POST $SLACK_WEBHOOK_URL -d "{\"text\":\"✅ Multi-tenancy deployed to production\"}"

# Update monitoring dashboards
echo "📊 Updating monitoring dashboards..."
# ... update Grafana dashboards

echo "✅ All done!"
```

---

### Step 7: Monitoring Setup (Day 5)

**File:** `monitoring/alerts.yml`

```yaml
# Prometheus alerting rules for multi-tenancy

groups:
  - name: multi_tenancy_alerts
    rules:
      # Tenant isolation violations
      - alert: TenantIsolationViolation
        expr: audit_events_total{event_type="tenant_isolation_violation"} > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Tenant isolation violation detected"
          description: "User {{ $labels.user_id }} attempted to access resources from organization {{ $labels.org_id }}"

      # High error rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # RLS query performance
      - alert: RLSQuerySlow
        expr: histogram_quantile(0.95, rate(query_duration_seconds_bucket{rls="enabled"}[5m])) > 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "RLS queries are slow"
          description: "95th percentile query time is {{ $value }}s (target: <0.1s)"

      # Invitation rate limit hit
      - alert: InvitationRateLimitExceeded
        expr: rate(rate_limit_exceeded_total{endpoint="invite"}[1h]) > 5
        for: 5m
        labels:
          severity: info
        annotations:
          summary: "Invitation rate limit frequently exceeded"
          description: "{{ $value }} invitations blocked by rate limit"

      # Quota exceeded
      - alert: OrganizationQuotaExceeded
        expr: organization_quota_exceeded_total > 0
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Organization quota exceeded"
          description: "Organization {{ $labels.org_id }} exceeded quota"

      # Database connection pool
      - alert: DatabasePoolExhausted
        expr: db_connection_pool_available < 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool nearly exhausted"
          description: "Only {{ $value }} connections available"

      # Email delivery failures
      - alert: EmailDeliveryFailure
        expr: rate(email_send_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Email delivery failures detected"
          description: "{{ $value }} emails failed to send"
```

---

### Step 8: Documentation Updates (Day 5)

**File:** `docs/multi-tenancy-user-guide.md`

```markdown
# Multi-Tenancy User Guide

## Getting Started

### Creating Your Organization

1. Click **Create Organization** from the dashboard
2. Enter organization name (e.g., "Acme Corp")
3. Choose a unique slug (e.g., "acme-corp") - this will be used in URLs
4. Click **Create**

You are now the **Owner** of the organization with full control.

## Managing Members

### Inviting Members

**Requirements:** Owner or Admin role

1. Navigate to **Organization → Members**
2. Click **Invite Member**
3. Enter email address
4. Select role:
   - **Admin:** Can invite members, manage groups, view all documents
   - **Member:** Can upload documents, create groups
   - **Viewer:** Can view public documents only
5. Click **Send Invitation**

The invitee will receive an email with a link to join (expires in 7 days).

### Managing Roles

**Owners** can change member roles:

1. Go to **Organization → Members**
2. Find the member
3. Click **Change Role**
4. Select new role
5. Confirm

### Removing Members

1. Go to **Organization → Members**
2. Find the member
3. Click **Remove**
4. Confirm

**Note:** Cannot remove the organization owner. Transfer ownership first.

## Groups

Groups allow you to organize members and grant document access to multiple people at once.

### Creating Groups

**Requirements:** Member role or higher

1. Navigate to **Organization → Groups**
2. Click **Create Group**
3. Enter name (e.g., "Engineering Team")
4. Add description (optional)
5. Click **Create**

### Adding Members to Groups

1. Go to **Organization → Groups**
2. Click on the group
3. Click **Add Members**
4. Select users
5. Click **Add**

## Document Visibility

Control who can see your documents.

### Visibility Levels

- **Public:** All organization members can view
- **Restricted:** Only selected users/groups can access
- **Private:** Only you and admins (default)

### Setting Visibility

1. Upload document or edit existing
2. Choose visibility level
3. If **Restricted**:
   - Select users or groups
   - Choose access level (View or Edit)
4. Save

### Granting Access

For restricted documents:

1. Go to document details
2. Click **Manage Access**
3. Add users or groups
4. Select access level
5. Click **Grant Access**

## Organization Settings

**Owners only:**

- Update organization name
- Configure quotas (future)
- Delete organization (all data will be lost)

## Quotas

Each organization has limits:

- **Documents:** 100 (default)
- **Storage:** 5GB (default)

Check usage in **Organization Dashboard**.

## Best Practices

### Security

1. Use strong passwords
2. Only invite trusted members
3. Regularly review member list
4. Use groups for easier access management
5. Set sensitive documents to **Private**

### Organization

1. Create groups for departments (Engineering, Sales, HR)
2. Use descriptive document names
3. Set appropriate visibility from the start
4. Remove inactive members

## Troubleshooting

### Can't invite member
- Check if you have Owner or Admin role
- Verify email address is correct
- Check if user is already a member

### Can't access document
- Check document visibility
- Verify you're a member of the organization
- For restricted docs, check if you have access grant

### Invitation not received
- Check spam folder
- Verify email address
- Ask sender to resend

## FAQ

**Q: Can I belong to multiple organizations?**
A: Currently, users can only belong to one organization.

**Q: What happens when I delete my organization?**
A: All documents and data are permanently deleted. This cannot be undone.

**Q: Can I transfer ownership?**
A: Yes, owners can transfer ownership to another admin. Both parties must confirm.

**Q: How do I increase quotas?**
A: Contact support to upgrade your plan (future feature).
```

---

## Testing Checklist

- [ ] Unit tests pass (coverage > 80%)
- [ ] Integration tests pass (all endpoints)
- [ ] E2E tests pass (critical flows)
- [ ] Security tests pass (100%)
- [ ] Performance tests pass (RLS < 10ms)
- [ ] Staging deployment successful
- [ ] UAT completed
- [ ] Production deployment successful
- [ ] Monitoring alerts configured
- [ ] Documentation updated

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests pass
- [ ] Code review approved
- [ ] Database backup created
- [ ] Rollback plan tested
- [ ] Users notified of maintenance

### Deployment
- [ ] Maintenance mode enabled (optional)
- [ ] Migrations run successfully
- [ ] Services deployed
- [ ] Health checks pass
- [ ] Smoke tests pass

### Post-Deployment
- [ ] Monitoring dashboards updated
- [ ] Alerts verified working
- [ ] User communication sent
- [ ] Support team briefed
- [ ] Documentation published

---

## Success Criteria

- Zero critical bugs in production
- < 5% error rate in first week
- No tenant isolation violations
- All performance targets met
- User feedback positive (>4/5 rating)

---

## Support & Maintenance

### Ongoing Tasks
- Monitor error rates daily
- Review security alerts
- Update documentation as needed
- Collect user feedback
- Plan feature enhancements

### Incident Response
1. Check monitoring dashboards
2. Review error logs
3. Check audit trail
4. Escalate if needed
5. Document incident
6. Post-mortem within 24 hours

---

## Completion

This completes the multi-tenancy implementation plan. All phases have been successfully delivered.

**Timeline:** 5 weeks
**Status:** Ready for implementation

**Next Steps:**
1. Review and approve plan
2. Set up project board
3. Begin Phase 1 implementation
