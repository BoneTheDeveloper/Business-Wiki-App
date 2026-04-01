"""Quota Pydantic schemas."""
from pydantic import BaseModel


class QuotaUsage(BaseModel):
    """Organization quota usage."""
    documents_used: int
    documents_limit: int
    storage_used_bytes: int
    storage_limit_bytes: int
    documents_percentage: float
    storage_percentage: float
