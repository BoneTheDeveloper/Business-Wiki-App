-- Document access control
CREATE TABLE document_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    group_id UUID REFERENCES groups(id) ON DELETE CASCADE,
    access_level VARCHAR(10) NOT NULL DEFAULT 'view' CHECK (access_level IN ('view', 'edit')),
    granted_by_id UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_access_target CHECK (
        (user_id IS NOT NULL AND group_id IS NULL) OR
        (user_id IS NULL AND group_id IS NOT NULL)
    )
);

CREATE INDEX ix_doc_access_document_id ON document_access (document_id);
CREATE INDEX ix_doc_access_user_id ON document_access (user_id);
CREATE INDEX ix_doc_access_group_id ON document_access (group_id);
CREATE INDEX ix_doc_access_composite ON document_access (document_id, user_id, group_id);

-- Email invitations to organizations
CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    invitee_email VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    token_salt VARCHAR(64) NOT NULL,
    invited_by_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    used BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX ix_invitations_org_id ON invitations (organization_id);
CREATE INDEX ix_invitations_email ON invitations (invitee_email);
CREATE INDEX ix_invitations_token_hash ON invitations (token_hash);

-- OAuth social accounts
CREATE TABLE social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    provider_email VARCHAR(255) NOT NULL,
    access_token VARCHAR(500),
    refresh_token VARCHAR(500),
    expires_at TIMESTAMPTZ,
    profile_data JSONB NOT NULL DEFAULT '{}',
    linked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_social_provider_user UNIQUE (provider, provider_user_id)
);

CREATE INDEX ix_social_accounts_user_id ON social_accounts (user_id);
CREATE INDEX ix_social_accounts_provider ON social_accounts (provider);
