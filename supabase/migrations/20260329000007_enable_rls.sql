-- Enable Row Level Security on all application tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE group_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_access ENABLE ROW LEVEL SECURITY;
ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_accounts ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (used by backend API)
-- These policies allow the backend (using service_role key) full access
-- while anon/authenticated users go through the API layer

-- Users: users can read own profile
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid() = id);

-- Documents: users can see their own + org documents
CREATE POLICY "Users can view own documents" ON documents
    FOR SELECT USING (user_id = auth.uid() OR organization_id IN (
        SELECT om.organization_id FROM organization_members om WHERE om.user_id = auth.uid()
    ));

CREATE POLICY "Users can create documents" ON documents
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own documents" ON documents
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "Users can delete own documents" ON documents
    FOR DELETE USING (user_id = auth.uid());

-- Document chunks: follow document visibility
CREATE POLICY "Users can view chunks of accessible documents" ON document_chunks
    FOR SELECT USING (document_id IN (
        SELECT d.id FROM documents d WHERE d.user_id = auth.uid() OR d.organization_id IN (
            SELECT om.organization_id FROM organization_members om WHERE om.user_id = auth.uid()
        )
    ));

-- Organization members can view org info
CREATE POLICY "Org members can view organization" ON organizations
    FOR SELECT USING (owner_id = auth.uid() OR id IN (
        SELECT om.organization_id FROM organization_members om WHERE om.user_id = auth.uid()
    ));

CREATE POLICY "Org members can view membership" ON organization_members
    FOR SELECT USING (user_id = auth.uid() OR organization_id IN (
        SELECT om.organization_id FROM organization_members om WHERE om.user_id = auth.uid()
    ));
