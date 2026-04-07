"""Supabase JWT verification using JWKS."""
import logging
import time
from typing import Optional

from jose import jwt, JWTError
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class JWKSCache:
    """Cache JWKS keys with TTL to avoid per-request network calls."""

    def __init__(self, ttl_seconds: int = 3600):
        self._jwks: Optional[dict] = None
        self._fetched_at: float = 0
        self._ttl = ttl_seconds

    async def get_jwks(self) -> dict:
        """Fetch JWKS from Supabase, using cache if fresh."""
        now = time.time()
        if self._jwks and (now - self._fetched_at) < self._ttl:
            return self._jwks

        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            self._jwks = resp.json()
            self._fetched_at = now
            return self._jwks


jwks_cache = JWKSCache()


async def verify_supabase_token(token: str) -> dict:
    """
    Verify a Supabase-issued JWT access token.

    Returns the decoded payload with claims:
    - sub: user UUID
    - email: user email
    - app_role: application role (from custom hook)
    - role: always "authenticated" (Postgres role, not app role)

    Raises HTTPException(401) on invalid/expired tokens.
    """
    from fastapi import HTTPException, status

    try:
        jwks = await jwks_cache.get_jwks()

        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
        )
        return payload

    except JWTError as e:
        logger.warning("JWT verification failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except httpx.HTTPError as e:
        logger.error("Cannot reach Supabase JWKS: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to verify token: {str(e)}",
        )
