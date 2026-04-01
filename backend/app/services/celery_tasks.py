"""Celery async tasks for document processing."""
import os
import tempfile
import asyncio
from typing import Dict, Any, List

from celery import shared_task
from sqlalchemy import select, delete

from app.config import settings


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(name="process_document", bind=True, max_retries=3)
def process_document_task(
    self,
    document_id: str,
    file_path: str,
    format_type: str
) -> Dict[str, Any]:
    """
    Process document: download, parse, chunk, embed.
    This is a Celery task that runs async operations.
    """
    async def _process() -> Dict[str, Any]:
        from app.models.database import AsyncSessionLocal
        from app.models.models import Document, DocumentStatus, DocumentChunk
        from app.services.minio_service import minio_service
        from app.services.parsing import DocumentParser
        from app.services.rag_service import rag_service

        async with AsyncSessionLocal() as db:
            # Get document
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                return {"error": "Document not found", "document_id": document_id}

            # Update status to processing
            doc.status = DocumentStatus.PROCESSING
            await db.commit()

            try:
                # Download file from MinIO
                content = await minio_service.get_file(file_path)

                # Save to temp file for parsing
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=f".{format_type}"
                ) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name

                try:
                    # Parse document
                    parsed = DocumentParser.parse(tmp_path, format_type)

                    # Update document metadata
                    doc.metadata = {
                        **doc.metadata,
                        **parsed['metadata'],
                        'text_length': len(parsed['text']),
                        'word_count': len(parsed['text'].split())
                    }

                    # Store extracted text (truncated)
                    doc.extracted_text = parsed['text'][:100000]

                    # Chunk and embed text
                    chunks = rag_service.chunk_text(parsed['text'], doc.metadata)
                    chunks_created = 0

                    if chunks and settings.GOOGLE_API_KEY:
                        # Batch embed for efficiency
                        contents = [c['content'] for c in chunks]
                        embeddings = await rag_service.embed_batch(contents)

                        # Store chunks with embeddings
                        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                            db_chunk = DocumentChunk(
                                document_id=doc.id,
                                content=chunk['content'],
                                embedding=embedding,
                                chunk_index=i,
                                metadata=chunk.get('metadata', {})
                            )
                            db.add(db_chunk)
                            chunks_created += 1

                        doc.doc_metadata['chunk_count'] = chunks_created

                    # Mark as completed
                    doc.status = DocumentStatus.COMPLETED
                    await db.commit()

                    return {
                        "document_id": document_id,
                        "status": "completed",
                        "metadata": doc.doc_metadata,
                        "chunks_created": chunks_created
                    }

                finally:
                    # Cleanup temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            except Exception as e:
                # Mark as failed
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)[:500]
                await db.commit()

                # Retry logic
                raise self.retry(exc=e, countdown=60)

    return run_async(_process())


@shared_task(name="delete_document_chunks")
def delete_document_chunks_task(document_id: str) -> Dict[str, Any]:
    """Delete all chunks for a document."""
    async def _delete():
        from app.models.database import AsyncSessionLocal
        from app.models.models import DocumentChunk

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.document_id == document_id
                )
            )
            await db.commit()
            return {"deleted_count": result.rowcount}

    return run_async(_delete())


@shared_task(name="reindex_document")
def reindex_document_task(document_id: str) -> Dict[str, Any]:
    """Reindex a document - delete existing chunks and re-process."""
    async def _reindex():
        from app.models.database import AsyncSessionLocal
        from app.models.models import Document, DocumentStatus
        from app.services.rag_service import rag_service

        async with AsyncSessionLocal() as db:
            # Get document
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                return {"error": "Document not found"}

            if not doc.extracted_text:
                return {"error": "No extracted text available"}

            # Delete existing chunks
            await db.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.document_id == document_id
                )
            )

            # Re-chunk and embed
            chunks = rag_service.chunk_text(doc.extracted_text, doc.metadata)
            chunks_created = 0

            if chunks and settings.GOOGLE_API_KEY:
                from app.models.models import DocumentChunk

                contents = [c['content'] for c in chunks]
                embeddings = await rag_service.embed_batch(contents)

                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    db_chunk = DocumentChunk(
                        document_id=doc.id,
                        content=chunk['content'],
                        embedding=embedding,
                        chunk_index=i,
                        metadata=chunk.get('metadata', {})
                    )
                    db.add(db_chunk)
                    chunks_created += 1

                doc.metadata['chunk_count'] = chunks_created
                await db.commit()

            return {"document_id": document_id, "chunks_created": chunks_created}

    return run_async(_reindex())
