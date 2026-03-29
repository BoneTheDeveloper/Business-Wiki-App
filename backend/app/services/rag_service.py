"""RAG service for chunking, embeddings, and vector search."""
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.config import settings


class RAGService:
    """RAG orchestration service for document processing and search."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.embed_model = "text-embedding-3-small"
        self.embed_dimensions = 1536
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,  # Characters (~512 tokens)
            chunk_overlap=200,  # ~50 tokens overlap
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

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

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")

        response = await self.client.embeddings.create(
            model=self.embed_model,
            input=text,
            dimensions=self.embed_dimensions
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batch for efficiency)."""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")

        if not texts:
            return []

        # Batch in groups of 100 (OpenAI limit)
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await self.client.embeddings.create(
                model=self.embed_model,
                input=batch,
                dimensions=self.embed_dimensions
            )
            all_embeddings.extend([item.embedding for item in response.data])

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
                1 - (dc.embedding <=> :embedding::vector) as similarity
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
        sql += f" ORDER BY dc.embedding <=> :embedding::vector LIMIT :limit"
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
