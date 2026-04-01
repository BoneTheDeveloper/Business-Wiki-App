-- Remove columns now managed by Supabase Auth
-- password_hash: Supabase Auth manages passwords
-- oauth_provider, oauth_id: Supabase Auth manages identities in auth.identities

ALTER TABLE public.users DROP COLUMN IF EXISTS password_hash;
ALTER TABLE public.users DROP COLUMN IF EXISTS oauth_provider;
ALTER TABLE public.users DROP COLUMN IF EXISTS oauth_id;

-- Drop OAuth-related indexes
DROP INDEX IF EXISTS public.ix_users_oauth_provider;
DROP INDEX IF EXISTS public.ix_users_oauth_provider_oauth_id;

-- Add RLS policy to allow the sync trigger (SECURITY DEFINER) to insert/update
-- The trigger runs as table owner, so it bypasses RLS. But add service role policy for backend.
-- Backend uses service_role key which bypasses RLS, so no additional policy needed.
