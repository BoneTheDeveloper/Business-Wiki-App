# Phase 1: Database Migration

**Priority:** P1 | **Status:** Pending | **Effort:** 1h

## Context

- Research: `plans/reports/researcher-260327-1108-google-oauth-implementation.md`
- Current User model: `backend/app/models/models.py`
- Current schema: users table with id, email, password_hash, role, is_active

## Overview

Add OAuth-related fields to the existing users table and create a new social_accounts table for multi-provider OAuth support.

## Key Insights

1. `password_hash` must become nullable for OAuth-only users
2. `social_accounts` table enables multiple OAuth providers per user
3. Index on (oauth_provider, oauth_id) for fast OAuth lookups
4. JSONB for flexible profile data storage

## Requirements

### Functional
- Store OAuth provider and provider user ID
- Support nullable password for OAuth-only accounts
- Track email verification status from OAuth
- Store optional name and avatar URL from OAuth

### Non-Functional
- Migration must be reversible
- Existing data must not be affected
- Indexes for query performance

## Architecture

```
users table (modified):
├── id (UUID, PK)
├── email (String, unique)
├── password_hash (String, nullable) ← CHANGED
├── email_verified (Boolean, nullable) ← NEW
├── oauth_provider (String, nullable) ← NEW
├── oauth_id (String, nullable) ← NEW
├── name (String, nullable) ← NEW
├── avatar_url (String, nullable) ← NEW
├── role (Enum)
├── is_active (Boolean)
├── created_at, updated_at

social_accounts table (new):
├── id (UUID, PK)
├── user_id (UUID, FK → users.id)
├── provider (String) - 'google', 'github', etc.
├── provider_user_id (String) - Provider's unique ID
├── provider_email (String)
├── access_token (String, nullable)
├── refresh_token (String, nullable)
├── expires_at (DateTime, nullable)
├── profile_data (JSONB)
├── linked_at, updated_at
```

## Related Code Files

### Modify
- `backend/app/models/models.py` - Add User fields, create SocialAccount model
- `backend/app/models/schemas.py` - Add OAuth-related response schemas

### Create
- `backend/app/models/migrations/001_add_oauth_fields.py` - Alembic migration

## Implementation Steps

### Step 1: Update User Model

```python
# backend/app/models/models.py

class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Changed to nullable
    email_verified = Column(Boolean, nullable=True)  # NEW
    oauth_provider = Column(String(50), nullable=True, index=True)  # NEW
    oauth_id = Column(String(255), nullable=True)  # NEW
    name = Column(String(255), nullable=True)  # NEW
    avatar_url = Column(String(500), nullable=True)  # NEW
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="user")
    social_accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_users_oauth_provider_oauth_id', 'oauth_provider', 'oauth_id'),
    )
```

### Step 2: Create SocialAccount Model

```python
# backend/app/models/models.py (append)

class SocialAccount(Base):
    """OAuth social account linking table."""
    __tablename__ = "social_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False, index=True)
    provider_user_id = Column(String(255), nullable=False, index=True)
    provider_email = Column(String(255), nullable=False)
    access_token = Column(String(500), nullable=True)
    refresh_token = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    profile_data = Column(JSONB, default=dict)
    linked_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="social_accounts")

    __table_args__ = (
        UniqueConstraint('provider', 'provider_user_id', name='uq_social_provider_user'),
        Index('ix_social_accounts_user_id', 'user_id'),
    )
```

### Step 3: Update Schemas

```python
# backend/app/models/schemas.py (add)

class UserResponse(BaseModel):
    """User response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    is_active: bool
    email_verified: Optional[bool] = None  # NEW
    name: Optional[str] = None  # NEW
    avatar_url: Optional[str] = None  # NEW
    oauth_provider: Optional[str] = None  # NEW
    created_at: datetime


class OAuthCallbackResponse(BaseModel):
    """OAuth callback response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new_user: bool = False
```

### Step 4: Create Alembic Migration

```python
# backend/app/models/migrations/versions/xxx_add_oauth_fields.py

def upgrade():
    # Add columns to users table
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('oauth_provider', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('oauth_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('name', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(500), nullable=True))

    # Alter password_hash to nullable
    op.alter_column('users', 'password_hash', nullable=True)

    # Create index for OAuth lookups
    op.create_index('ix_users_oauth_provider_oauth_id', 'users', ['oauth_provider', 'oauth_id'])

    # Create social_accounts table
    op.create_table(
        'social_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=False),
        sa.Column('provider_email', sa.String(255), nullable=False),
        sa.Column('access_token', sa.String(500), nullable=True),
        sa.Column('refresh_token', sa.String(500), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('profile_data', postgresql.JSONB, nullable=True),
        sa.Column('linked_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('provider', 'provider_user_id', name='uq_social_provider_user')
    )

    op.create_index('ix_social_accounts_user_id', 'social_accounts', ['user_id'])
    op.create_index(op.f('ix_social_accounts_provider'), 'social_accounts', ['provider'])


def downgrade():
    op.drop_index(op.f('ix_social_accounts_provider'), table_name='social_accounts')
    op.drop_index('ix_social_accounts_user_id', table_name='social_accounts')
    op.drop_table('social_accounts')

    op.drop_index('ix_users_oauth_provider_oauth_id', table_name='users')
    op.alter_column('users', 'password_hash', nullable=False)
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'name')
    op.drop_column('users', 'oauth_id')
    op.drop_column('users', 'oauth_provider')
    op.drop_column('users', 'email_verified')
```

## Todo List

- [ ] Update User model in models.py
- [ ] Create SocialAccount model
- [ ] Update UserResponse schema
- [ ] Create OAuthCallbackResponse schema
- [ ] Generate Alembic migration
- [ ] Run migration locally
- [ ] Verify migration success

## Success Criteria

- [ ] Migration runs without errors
- [ ] Existing users unaffected
- [ ] New columns added correctly
- [ ] social_accounts table created
- [ ] Indexes created for OAuth lookups
- [ ] Migration is reversible (downgrade works)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data loss on password_hash | High | Test on copy first, backup before migration |
| Migration failure | Medium | Wrap in transaction, test rollback |

## Security Considerations

- OAuth tokens in social_accounts should be encrypted at rest (future enhancement)
- Profile data in JSONB should be sanitized

## Next Steps

After completion:
- Proceed to Phase 2: Backend OAuth Endpoints
- Parallel: Phase 4 can start (Google Cloud Console setup)
