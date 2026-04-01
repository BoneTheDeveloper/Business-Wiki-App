-- Custom access token hook: inject app_role claim into JWT
-- This function runs before JWT issuance and adds the user's app role
-- from public.users into the JWT claims.

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

  IF user_role IS NOT NULL THEN
    claims := jsonb_set(claims, '{app_role}', to_jsonb(user_role));
  END IF;

  RETURN claims;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execution to supabase_functions_admin (GoTrue uses this role)
GRANT EXECUTE ON FUNCTION public.custom_access_token(JSONB) TO supabase_functions_admin;
