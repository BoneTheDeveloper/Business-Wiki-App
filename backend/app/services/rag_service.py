"""RAG service for chunking, embeddings, and vector search."""
from typing import List, Dict, Any, Optional

import numpy as np
from google import genai
from google.genai import types
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings


class RAGService:
    """RAG orchestration service for document processing and search."""

    def __init__(self):
        self._client: Optional[genai.Client] = None
        self.embed_model = "gemini-embedding-001"
        self.embed_dimensions = 1536
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,  # Characters (~512 tokens)
            chunk_overlap=200,  # ~50 tokens overlap
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    @property
    def client(self) -> genai.Client:
        """Lazy-init client to avoid crash when GOOGLE_API_KEY is empty."""
        if self._client is None:
            self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        return self._client

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Split text into chunks with metadata preservation."""
        chunks = self.splitter.split_text(text)
        base_metadata = metadata or {}

        return [
            {
                "content": chunk,
                "metadata": {
                    **base_metadata,
                    "chunk_index": i,
                    "char_count": len(chunk),
                    "word_count": len(chunk.split()),
                }
            }
            for i, chunk in enumerate(chunks)
        ]

    @staticmethod
    def _normalize(values: list[float]) -> list[float]:
        """L2-normalize embedding vector for accurate cosine similarity."""
        arr = np.array(values, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm == 0:
            return values
        return (arr / norm).tolist()

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text, L2-normalized."""
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not configured")
        try:
            result = await self.client.aio.models.embed_content(
                model=self.embed_model,
                contents=[text],
                config=types.EmbedContentConfig(
                    output_dimensionality=self.embed_dimensions
                )
            )
            return self._normalize(result.embeddings[0].values)
        except Exception as e:
            raise RuntimeError(f"Embedding failed: {e}") from e

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts, all L2-normalized."""
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not configured")

        if not texts:
            return []

        # Gemini handles batching natively; chunk to 100 for safety
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            result = await self.client.aio.models.embed_content(
                model=self.embed_model,
                contents=batch,
                config=types.EmbedContentConfig(
                    output_dimensionality=self.embed_dimensions
                )
            )
            all_embeddings.extend(
                [self._normalize(e.values) for e in result.embeddings]
            )

        return all_embeddings

    async def search(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 10,
        document_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search with optional filters.

        Uses pgvector cosine distance (<=>) for similarity.
        Returns results sorted by similarity score.
        """
        # Generate query embedding
        query_embedding = await self.embed(query)

        # Build SQL query with vector similarity search
        sql = """
            SELECT
                dc.id,
                dc.content,
                dc.chunk_metadata,
                dc.document_id,
                d.filename,
                d.format,
                1 - (dc.embedding <=> CAST(:embedding AS vector)) as similarity
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE d.status = 'completed'
        """
        params = {"embedding": str(query_embedding)}

        # Add document ID filter
        if document_ids:
            sql += " AND dc.document_id = ANY(:doc_ids::uuid[])"
            params["doc_ids"] = document_ids

        # Add optional filters
        if filters:
            if filters.get("format"):
                sql += " AND d.format = :format"
                params["format"] = filters["format"]

            if filters.get("user_id"):
                sql += " AND d.user_id = :user_id::uuid"
                params["user_id"] = filters["user_id"]

        # Order by similarity (lower distance = higher similarity)
        sql += f" ORDER BY dc.embedding <=> CAST(:embedding AS vector) LIMIT :limit"
        params["limit"] = min(top_k, 50)

        result = await db.execute(text(sql), params)
        rows = result.fetchall()

        return [
            {
                "chunk_id": str(row.id),
                "content": row.content,
                "metadata": row.chunk_metadata or {},
                "document_id": str(row.document_id),
                "filename": row.filename,
                "format": row.format,
                "similarity": round(float(row.similarity), 4)
            }
            for row in rows
        ]


# Singleton instance
rag_service = RAGService()
