"""Auth-related Pydantic schemas -- Supabase JWT payload typing."""
from pydantic import BaseModel
from typing import Optional


class SupabaseUserPayload(BaseModel):
    """Decoded Supabase JWT payload (internal typing only)."""
    sub: str  # user UUID
    email: str
    role: str  # always "authenticated" (Postgres role)
    app_role: Optional[str] = None  # injected by custom access token hook
    email_confirmed: Optional[bool] = None
