"""Security utilities -- Supabase JWT validation only."""
# All auth operations (signup, login, password reset, OAuth) handled by Supabase.
# This module re-exports the JWT verification function for use in dependencies.

from app.auth.supabase import verify_supabase_token, jwks_cache

__all__ = ["verify_supabase_token", "jwks_cache"]
