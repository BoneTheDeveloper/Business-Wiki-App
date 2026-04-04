-- Fix custom_access_token hook: wrong GRANT role + race condition fallback + RLS policy
-- Bug 1: Granted to supabase_functions_admin instead of supabase_auth_admin (caused 500 error)
-- Bug 2: No fallback when public.users row doesn't exist yet (OAuth signup race condition)
-- Bug 3: Missing RLS policy for supabase_auth_admin on public.users

-- Recreate function with fallback logic
CREATE OR REPLACE FUNCTION public.custom_access_token(event JSONB)
RETURNS JSONB AS $$
DECLARE
  claims JSONB;
  user_role VARCHAR(20);
BEGIN
  claims := event->'claims';

  -- Look up app role from public.users
  SELECT role INTO user_role
  FROM public.users
  WHERE id = (event->>'sub')::UUID;

  -- Default to 'user' if row not found (race condition during OAuth signup)
  IF user_role IS NULL THEN
    user_role := 'user';
  END IF;

  claims := jsonb_set(claims, '{app_role}', to_jsonb(user_role));

  -- Return event with updated claims (Supabase expected format)
  RETURN jsonb_set(event, '{claims}', claims);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Correct grant: supabase_auth_admin, NOT supabase_functions_admin
GRANT EXECUTE ON FUNCTION public.custom_access_token(JSONB) TO supabase_auth_admin;

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO supabase_auth_admin;

-- Revoke from public roles
REVOKE EXECUTE ON FUNCTION public.custom_access_token(JSONB) FROM authenticated, anon, public;

-- Allow auth admin to read user roles (for custom_access_token hook)
CREATE POLICY "Auth admin can read users" ON public.users
  AS PERMISSIVE FOR SELECT
  TO supabase_auth_admin
  USING (true);
