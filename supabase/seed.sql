-- Seed data for local development
-- Run with: supabase db reset

-- Test user (password: "testpassword123" - bcrypt hash)
INSERT INTO users (id, email, password_hash, name, role, is_active) VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'admin@example.com', '$2b$12$LJ3m4ys3Lg2RqwmMpVr5kuYDFnGMHbOlcEHjPMYVHNwiMbEMwvoFW', 'Admin User', 'admin', TRUE),
    ('b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'editor@example.com', '$2b$12$LJ3m4ys3Lg2RqwmMpVr5kuYDFnGMHbOlcEHjPMYVHNwiMbOlcEHj', 'Editor User', 'editor', TRUE),
    ('c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'user@example.com', '$2b$12$LJ3m4ys3Lg2RqwmMpVr5kuYDFnGMHbOlcEHjPMYVHNwiMbOlcEHj', 'Regular User', 'user', TRUE);

-- Test organization
INSERT INTO organizations (id, name, slug, owner_id, max_documents, max_storage_bytes) VALUES
    ('d3eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'Acme Corp', 'acme-corp', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 100, 5368709120);

-- Organization memberships
INSERT INTO organization_members (organization_id, user_id, role, invited_by_id) VALUES
    ('d3eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'owner', NULL),
    ('d3eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'admin', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'),
    ('d3eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'member', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11');
