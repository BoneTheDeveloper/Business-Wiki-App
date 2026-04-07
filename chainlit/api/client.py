"""HTTP client for backend playground API — shared connection pool."""
import os
from typing import Optional

import httpx

from api.models import SearchResponse, ChatResponse, DocumentsResponse

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_PREFIX = "/api/v1/playground"
TIMEOUT = 60.0

# Shared async client — reused across requests for connection pooling
_client: Optional[httpx.AsyncClient] = None


async def _get_client() -> httpx.AsyncClient:
    """Get or create the shared httpx async client."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=BACKEND_URL,
            timeout=TIMEOUT,
        )
    return _client


async def search(
    query: str,
    top_k: int = 10,
    document_ids: Optional[list[str]] = None,
) -> SearchResponse:
    """Call playground search endpoint."""
    payload: dict = {"query": query, "top_k": top_k}
    if document_ids:
        payload["document_ids"] = document_ids

    client = await _get_client()
    resp = await client.post(f"{API_PREFIX}/search", json=payload)
    resp.raise_for_status()
    return SearchResponse(**resp.json())


async def chat(
    query: str,
    top_k: int = 5,
    document_ids: Optional[list[str]] = None,
    conversation_history: Optional[list[dict]] = None,
) -> ChatResponse:
    """Call playground chat endpoint."""
    payload: dict = {"query": query, "top_k": top_k}
    if document_ids:
        payload["document_ids"] = document_ids
    if conversation_history:
        payload["conversation_history"] = conversation_history

    client = await _get_client()
    resp = await client.post(f"{API_PREFIX}/chat", json=payload)
    resp.raise_for_status()
    return ChatResponse(**resp.json())


async def list_documents() -> DocumentsResponse:
    """List available documents from backend."""
    client = await _get_client()
    resp = await client.get(f"{API_PREFIX}/documents", timeout=30.0)
    resp.raise_for_status()
    return DocumentsResponse(**resp.json())
