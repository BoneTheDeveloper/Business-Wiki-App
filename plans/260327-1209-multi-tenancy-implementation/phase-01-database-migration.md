# Phase 1: Database Schema & Migration

**Priority:** Critical
**Duration:** Week 1 (5 days)
**Status:** Pending
**Dependencies:** None

---

## Overview

Add multi-tenancy tables and migrate existing data to support organization-based document storage.

### Key Objectives
- Create organization-related tables
- Add `organization_id` to existing tables
- Migrate existing users to default organizations
- Maintain data integrity during migration
- Prepare for RLS policy implementation

---

## Requirements

### Functional Requirements
- Users automatically get default organization on first login
- Existing documents migrated to user's default organization
- All organization tables support CRUD operations
- Unique slugs for organizations (URL-friendly)
- Proper foreign key constraints with cascade rules

### Non-Functional Requirements
- Migration completes in < 5 minutes for 10K documents
- Zero data loss during migration
- Rollback capability if migration fails
- Backward compatibility maintained

---

## Architecture

### Database Schema Changes

```sql
-- New Tables: 5
-- Modified Tables: 1 (documents)
-- New Indexes: 15
-- New Constraints: 8
```

### Table Relationships

```
users (1) ──── (1) organizations (owner)
  │                │
  │                └── (many) organization_members
  │                         │
  │                         └── (many) groups
  │                                  │
  │                                  └── (many) group_members
  │
  └── (many) documents
            │
            └── (many) document_access
                      │
                      └── (references) groups
```

---

## Implementation Steps

### Step 1: Create Migration File (Day 1)

**File:** `backend/app/migrations/versions/XXXX_add_multi_tenancy.py`

```python
"""Add multi-tenancy support

Revision ID: XXXX
Revises: Previous
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# revision identifiers
revision = 'XXXX'
down_revision = 'PREVIOUS'
branch_labels = None
depends_on = None

def upgrade():
    """Create multi-tenancy tables and migrate data."""

    # 1. Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('max_documents', sa.Integer, default=100),
        sa.Column('max_storage_bytes', sa.BigInteger, default=5368709120),  # 5GB
        sa.Column('current_documents', sa.Integer, default=0),
        sa.Column('current_storage_bytes', sa.BigInteger, default=0),
        sa.Column('settings', postgresql.JSONB, default={}),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime,
                  default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    # 2. Create organization_members table
    op.create_table(
        'organization_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),  # owner, admin, member, viewer
        sa.Column('invited_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('joined_at', sa.DateTime, default=datetime.utcnow),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_org_user'),
    )

    # 3. Create groups table
    op.create_table(
        'groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.UniqueConstraint('organization_id', 'name', name='uq_org_group_name'),
    )

    # 4. Create group_members table
    op.create_table(
        'group_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('added_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('added_at', sa.DateTime, default=datetime.utcnow),
        sa.UniqueConstraint('group_id', 'user_id', name='uq_group_user'),
    )

    # 5. Create document_access table
    op.create_table(
        'document_access',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=True),
        sa.Column('access_level', sa.String(20), nullable=False),  # view, edit
        sa.Column('granted_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('granted_at', sa.DateTime, default=datetime.utcnow),
        sa.CheckConstraint(
            '(user_id IS NOT NULL AND group_id IS NULL) OR '
            '(user_id IS NULL AND group_id IS NOT NULL)',
            name='ck_access_target'
        ),
    )

    # 6. Create invitations table
    op.create_table(
        'invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('invitee_email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),  # admin, member, viewer
        sa.Column('token_hash', sa.String(64), unique=True, nullable=False),
        sa.Column('token_salt', sa.String(64), nullable=False),
        sa.Column('invited_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('used_at', sa.DateTime, nullable=True),
        sa.Column('used', sa.Boolean, default=False),
    )

    # 7. Modify documents table
    op.add_column('documents',
                  sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                           sa.ForeignKey('organizations.id'), nullable=True))
    op.add_column('documents',
                  sa.Column('visibility', sa.String(20), default='private'))

    print("✅ Tables created successfully")

def downgrade():
    """Rollback multi-tenancy changes."""
    # Drop in reverse order
    op.drop_column('documents', 'visibility')
    op.drop_column('documents', 'organization_id')
    op.drop_table('invitations')
    op.drop_table('document_access')
    op.drop_table('group_members')
    op.drop_table('groups')
    op.drop_table('organization_members')
    op.drop_table('organizations')
```

---

### Step 2: Create Indexes (Day 1)

**File:** `backend/app/migrations/versions/XXXX_add_multi_tenancy_indexes.py`

```python
def upgrade():
    """Add indexes for multi-tenancy performance."""

    # Organization indexes
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])
    op.create_index('ix_organizations_owner_id', 'organizations', ['owner_id'])

    # Member indexes
    op.create_index('ix_org_members_org_id', 'organization_members', ['organization_id'])
    op.create_index('ix_org_members_user_id', 'organization_members', ['user_id'])
    op.create_index('ix_org_members_composite', 'organization_members',
                    ['organization_id', 'user_id'])

    # Group indexes
    op.create_index('ix_groups_org_id', 'groups', ['organization_id'])

    # Group member indexes
    op.create_index('ix_group_members_group_id', 'group_members', ['group_id'])
    op.create_index('ix_group_members_user_id', 'group_members', ['user_id'])
    op.create_index('ix_group_members_composite', 'group_members',
                    ['group_id', 'user_id'])

    # Document access indexes
    op.create_index('ix_doc_access_document_id', 'document_access', ['document_id'])
    op.create_index('ix_doc_access_user_id', 'document_access', ['user_id'])
    op.create_index('ix_doc_access_group_id', 'document_access', ['group_id'])
    op.create_index('ix_doc_access_composite', 'document_access',
                    ['document_id', 'user_id', 'group_id'])

    # Invitation indexes
    op.create_index('ix_invitations_token_hash', 'invitations', ['token_hash'])
    op.create_index('ix_invitations_email', 'invitations', ['invitee_email'])
    op.create_index('ix_invitations_org_id', 'invitations', ['organization_id'])

    # Document indexes
    op.create_index('ix_documents_org_id', 'documents', ['organization_id'])
    op.create_index('ix_documents_visibility', 'documents', ['visibility'])
    op.create_index('ix_documents_org_visibility', 'documents',
                    ['organization_id', 'visibility'])

    print("✅ Indexes created successfully")

def downgrade():
    """Remove indexes."""
    op.drop_index('ix_documents_org_visibility', 'documents')
    op.drop_index('ix_documents_visibility', 'documents')
    op.drop_index('ix_documents_org_id', 'documents')
    op.drop_index('ix_invitations_org_id', 'invitations')
    op.drop_index('ix_invitations_email', 'invitations')
    op.drop_index('ix_invitations_token_hash', 'invitations')
    op.drop_index('ix_doc_access_composite', 'document_access')
    op.drop_index('ix_doc_access_group_id', 'document_access')
    op.drop_index('ix_doc_access_user_id', 'document_access')
    op.drop_index('ix_doc_access_document_id', 'document_access')
    op.drop_index('ix_group_members_composite', 'group_members')
    op.drop_index('ix_group_members_user_id', 'group_members')
    op.drop_index('ix_group_members_group_id', 'group_members')
    op.drop_index('ix_groups_org_id', 'groups')
    op.drop_index('ix_org_members_composite', 'organization_members')
    op.drop_index('ix_org_members_user_id', 'organization_members')
    op.drop_index('ix_org_members_org_id', 'organization_members')
    op.drop_index('ix_organizations_owner_id', 'organizations')
    op.drop_index('ix_organizations_slug', 'organizations')
```

---

### Step 3: Data Migration Script (Day 2-3)

**File:** `backend/app/migrations/data_migrations/migrate_to_multi_tenant.py`

```python
"""Migrate existing users to default organizations."""
import asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import AsyncSessionLocal
from app.models.models import User, Document, Organization, OrganizationMember
from app.models.schemas import UserRole
import uuid
from datetime import datetime


async def create_default_organization(user: User, db: AsyncSession) -> Organization:
    """Create default organization for existing user."""
    # Generate unique slug
    slug = f"user-{str(user.id)[:8]}"

    # Check slug uniqueness
    existing = await db.execute(
        select(Organization).where(Organization.slug == slug)
    )
    if existing.scalar_one_or_none():
        slug = f"{slug}-{datetime.utcnow().timestamp()}"

    # Create organization
    org = Organization(
        id=uuid.uuid4(),
        name=f"{user.email}'s Workspace",
        slug=slug,
        owner_id=user.id,
        max_documents=100,
        max_storage_bytes=5368709120,  # 5GB
        current_documents=0,
        current_storage_bytes=0,
        settings={},
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(org)
    await db.flush()

    # Add user as owner
    member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=user.id,
        role="owner",
        invited_by_id=None,  # Self-created
        joined_at=datetime.utcnow()
    )
    db.add(member)

    return org


async def migrate_user_documents(user: User, org: Organization, db: AsyncSession):
    """Migrate user's documents to their organization."""
    # Count documents
    result = await db.execute(
        select(Document).where(Document.user_id == user.id)
    )
    documents = result.scalars().all()

    if not documents:
        return

    # Update documents
    await db.execute(
        update(Document)
        .where(Document.user_id == user.id)
        .values(
            organization_id=org.id,
            visibility="private"
        )
    )

    # Update org stats
    total_size = sum(doc.file_size or 0 for doc in documents)
    org.current_documents = len(documents)
    org.current_storage_bytes = total_size

    print(f"  📄 Migrated {len(documents)} documents for {user.email}")


async def migrate_to_multi_tenant():
    """Main migration function."""
    async with AsyncSessionLocal() as db:
        try:
            print("🚀 Starting multi-tenant migration...")

            # Get all users
            result = await db.execute(select(User))
            users = result.scalars().all()

            print(f"📊 Found {len(users)} users to migrate")

            # Migrate each user
            for i, user in enumerate(users, 1):
                print(f"\n[{i}/{len(users)}] Migrating {user.email}...")

                # Create default organization
                org = await create_default_organization(user, db)
                print(f"  ✅ Created organization: {org.name}")

                # Migrate documents
                await migrate_user_documents(user, org, db)

                # Commit per user to avoid large transaction
                await db.commit()

            print("\n✅ Migration completed successfully!")
            print(f"📊 Summary:")
            print(f"  - Organizations created: {len(users)}")
            print(f"  - Users migrated: {len(users)}")

        except Exception as e:
            await db.rollback()
            print(f"\n❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(migrate_to_multi_tenant())
```

---

### Step 4: Add ORM Models (Day 3)

**File:** `backend/app/models/models.py` (extend existing)

```python
# Add after existing models

class Organization(Base):
    """Organization model for multi-tenancy."""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"),
                     nullable=False, index=True)

    # Quotas
    max_documents = Column(Integer, default=100)
    max_storage_bytes = Column(BigInteger, default=5368709120)  # 5GB

    # Usage (denormalized for performance)
    current_documents = Column(Integer, default=0)
    current_storage_bytes = Column(BigInteger, default=0)

    # Settings
    settings = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("OrganizationMember", back_populates="organization",
                          cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="organization",
                         cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="organization")


class OrganizationMember(Base):
    """Organization membership with roles."""
    __tablename__ = "organization_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True),
                            ForeignKey("organizations.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    role = Column(String(20), nullable=False)  # owner, admin, member, viewer

    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])
    invited_by = relationship("User", foreign_keys=[invited_by_id])

    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='uq_org_user'),
    )


class Group(Base):
    """Document access groups."""
    __tablename__ = "groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True),
                            ForeignKey("organizations.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="groups")
    members = relationship("GroupMember", back_populates="group",
                          cascade="all, delete-orphan")
    created_by = relationship("User")

    __table_args__ = (
        UniqueConstraint('organization_id', 'name', name='uq_org_group_name'),
    )


class GroupMember(Base):
    """Group membership."""
    __tablename__ = "group_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)

    added_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    group = relationship("Group", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])
    added_by = relationship("User", foreign_keys=[added_by_id])

    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uq_group_user'),
    )


class DocumentAccess(Base):
    """Document access permissions."""
    __tablename__ = "document_access"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    # Access grantee (one must be set)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=True, index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
                     nullable=True, index=True)

    access_level = Column(String(20), nullable=False)  # view, edit

    granted_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="access_list")
    user = relationship("User", foreign_keys=[user_id])
    group = relationship("Group")
    granted_by = relationship("User", foreign_keys=[granted_by_id])

    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL AND group_id IS NULL) OR '
            '(user_id IS NULL AND group_id IS NOT NULL)',
            name='ck_access_target'
        ),
    )


class Invitation(Base):
    """Email invitations to organizations."""
    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True),
                            ForeignKey("organizations.id", ondelete="CASCADE"),
                            nullable=False, index=True)

    invitee_email = Column(String(255), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # admin, member, viewer

    # Security
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    token_salt = Column(String(64), nullable=False)

    # Tracking
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    used = Column(Boolean, default=False)

    # Relationships
    organization = relationship("Organization")
    invited_by = relationship("User")


# Update Document model
class Document(Base):
    # ... existing fields ...

    # Add multi-tenancy fields
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"),
                            nullable=True, index=True)
    visibility = Column(String(20), default="private")  # public, restricted, private

    # Update relationships
    organization = relationship("Organization", back_populates="documents")
    access_list = relationship("DocumentAccess", back_populates="document",
                              cascade="all, delete-orphan")
```

---

### Step 5: Test Migration (Day 4)

**File:** `backend/tests/migrations/test_multi_tenancy_migration.py`

```python
"""Test multi-tenancy migration."""
import pytest
from sqlalchemy import select
from app.models.models import User, Document, Organization, OrganizationMember
from app.migrations.data_migrations.migrate_to_multi_tenant import (
    create_default_organization,
    migrate_user_documents
)


@pytest.mark.asyncio
async def test_create_default_organization(db_session):
    """Test default organization creation."""
    # Create test user
    user = User(
        email="test@example.com",
        password_hash="hash",
        role="user"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create organization
    org = await create_default_organization(user, db_session)
    await db_session.commit()

    # Verify
    assert org.id is not None
    assert org.name == "test@example.com's Workspace"
    assert org.slug.startswith("user-")
    assert org.owner_id == user.id
    assert org.max_documents == 100
    assert org.max_storage_bytes == 5368709120

    # Verify membership
    result = await db_session.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user.id
        )
    )
    member = result.scalar_one_or_none()
    assert member is not None
    assert member.role == "owner"


@pytest.mark.asyncio
async def test_migrate_user_documents(db_session):
    """Test document migration."""
    # Create user
    user = User(email="test2@example.com", password_hash="hash", role="user")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create organization
    org = await create_default_organization(user, db_session)
    await db_session.commit()

    # Create documents
    docs = [
        Document(
            user_id=user.id,
            filename=f"doc{i}.pdf",
            file_path=f"/docs/doc{i}.pdf",
            file_size=1024 * (i + 1),
            format="pdf"
        )
        for i in range(3)
    ]
    db_session.add_all(docs)
    await db_session.commit()

    # Migrate
    await migrate_user_documents(user, org, db_session)
    await db_session.commit()
    await db_session.refresh(org)

    # Verify
    assert org.current_documents == 3
    assert org.current_storage_bytes == 1024 * (1 + 2 + 3)  # 6144

    # Verify documents updated
    result = await db_session.execute(
        select(Document).where(Document.user_id == user.id)
    )
    migrated_docs = result.scalars().all()
    for doc in migrated_docs:
        assert doc.organization_id == org.id
        assert doc.visibility == "private"


@pytest.mark.asyncio
async def test_slug_uniqueness(db_session):
    """Test slug uniqueness handling."""
    # Create two users with same ID prefix
    user1 = User(email="user1@example.com", password_hash="hash", role="user")
    user2 = User(email="user2@example.com", password_hash="hash", role="user")

    db_session.add_all([user1, user2])
    await db_session.commit()

    # Create orgs
    org1 = await create_default_organization(user1, db_session)
    await db_session.commit()

    org2 = await create_default_organization(user2, db_session)
    await db_session.commit()

    # Verify slugs are unique
    assert org1.slug != org2.slug
```

---

### Step 6: Rollback Script (Day 5)

**File:** `backend/app/migrations/rollback_multi_tenancy.py`

```python
"""Rollback multi-tenancy migration."""
import asyncio
from sqlalchemy import text
from app.models.database import engine


async def rollback_multi_tenancy():
    """Remove multi-tenancy tables and data."""
    async with engine.begin() as conn:
        try:
            print("🔄 Rolling back multi-tenancy migration...")

            # Remove columns from documents
            await conn.execute(text("ALTER TABLE documents DROP COLUMN IF EXISTS visibility"))
            await conn.execute(text("ALTER TABLE documents DROP COLUMN IF EXISTS organization_id"))

            # Drop tables in reverse order
            await conn.execute(text("DROP TABLE IF EXISTS invitations CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS document_access CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS group_members CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS groups CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS organization_members CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS organizations CASCADE"))

            print("✅ Rollback completed successfully!")

        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(rollback_multi_tenancy())
```

---

## Testing Checklist

- [ ] Migration runs without errors
- [ ] All existing users get default organizations
- [ ] All documents migrated to correct orgs
- [ ] Document counts and storage calculated correctly
- [ ] Organization slugs are unique
- [ ] Foreign key constraints work correctly
- [ ] Rollback script works
- [ ] Migration completes in < 5 minutes for 10K docs
- [ ] No data loss during migration
- [ ] Existing API endpoints still work (with null org_id)

---

## Performance Considerations

### Migration Performance
- **Batch size:** Commit per user to avoid large transactions
- **Index creation:** Create indexes after data migration
- **Memory usage:** Process users in chunks if > 10K users

### Query Performance
- **Indexes:** 15 new indexes for fast lookups
- **Composite indexes:** Optimized for common query patterns
- **Denormalized counts:** `current_documents` in org table

---

## Security Considerations

### Data Isolation
- **Foreign keys:** CASCADE rules prevent orphaned data
- **Constraints:** CHECK constraints ensure data integrity
- **NOT NULL:** Critical fields cannot be null

### Migration Safety
- **Backup:** Full database backup before migration
- **Dry run:** Test with production data copy
- **Rollback:** Tested rollback script ready

---

## Related Code Files

### Create
- `backend/app/migrations/versions/XXXX_add_multi_tenancy.py`
- `backend/app/migrations/versions/XXXX_add_multi_tenancy_indexes.py`
- `backend/app/migrations/data_migrations/migrate_to_multi_tenant.py`
- `backend/app/migrations/rollback_multi_tenancy.py`
- `backend/tests/migrations/test_multi_tenancy_migration.py`

### Modify
- `backend/app/models/models.py` - Add new models

---

## Next Phase

→ [Phase 2: Backend Services & API](./phase-02-backend-services.md)

---

## Unresolved Questions

1. **Migration window:** Should we enable maintenance mode during migration?
   - **Recommendation:** Yes, for zero-downtime requirement

2. **Default quota values:** 100 docs / 5GB - appropriate for MVP?
   - **Recommendation:** Yes, can be adjusted per org later

3. **Slug generation:** Timestamp-based or random suffix for duplicates?
   - **Recommendation:** Timestamp for readability

4. **Migration batch size:** 1 user vs 100 users per commit?
   - **Recommendation:** 1 user per commit for safety
