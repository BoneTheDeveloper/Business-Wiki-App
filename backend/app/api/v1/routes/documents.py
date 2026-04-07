"""Document management API routes."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
import uuid
import logging

from app.models.database import get_db
from app.models.models import Document, DocumentStatus, DocumentVisibility, User
from app.schemas.document import (
    DocumentResponse, DocumentList, DocumentVisibilityUpdate,
    DocumentAccessGrant, DocumentAccessResponse,
)
from app.dependencies import get_current_user
from app.services.minio_service import minio_service
from app.services.parsing import DocumentParser
from app.services.organization_service import organization_service
from app.services.permission_service import permission_service, Permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# File size limit: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


async def _get_document_with_access(
    doc_id: str,
    db: AsyncSession,
    user: User,
    require_edit: bool = False
) -> Document:
    """Fetch document and verify access permission. Raises HTTPException if not found or denied."""
    try:
        parsed_id = uuid.UUID(doc_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail="Document not found")

    result = await db.execute(
        select(Document).where(Document.id == parsed_id)
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    checker = permission_service.can_modify_document if require_edit else permission_service.check_document_access
    if not await checker(db, doc, user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return doc


async def _process_document_background(document_id: str, file_path: str, format_type: str):
    """Background task to process uploaded document."""
    import asyncio
    from app.services.celery_tasks import run_async
    from app.services.celery_tasks import process_document_task

    try:
        # Run the same processing logic from celery_tasks but without Celery
        async def _process():
            from app.models.database import AsyncSessionLocal
            from app.models.models import Document, DocumentStatus, DocumentChunk
            from app.services.minio_service import minio_service
            from app.services.parsing import DocumentParser
            from app.services.rag_service import rag_service
            from app.config import settings
            import tempfile
            import os

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Document).where(Document.id == document_id)
                )
                doc = result.scalar_one_or_none()
                if not doc:
                    return

                doc.status = DocumentStatus.PROCESSING
                await db.commit()

                try:
                    content = await minio_service.get_file(file_path)

                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=f".{format_type}"
                    ) as tmp:
                        tmp.write(content)
                        tmp_path = tmp.name

                    try:
                        parsed = DocumentParser.parse(tmp_path, format_type)

                        doc.doc_metadata = {
                            **doc.doc_metadata,
                            **parsed['metadata'],
                            'text_length': len(parsed['text']),
                            'word_count': len(parsed['text'].split())
                        }
                        doc.extracted_text = parsed['text'][:100000]

                        chunks = rag_service.chunk_text(parsed['text'], doc.doc_metadata)
                        chunks_created = 0

                        if chunks and settings.GOOGLE_API_KEY:
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

                            doc.doc_metadata['chunk_count'] = chunks_created

                        doc.status = DocumentStatus.COMPLETED
                        await db.commit()

                    finally:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)

                except Exception as e:
                    logger.error("Document processing failed for %s: %s", document_id, str(e))
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = str(e)[:500]
                    await db.commit()

        await _process()
    except Exception as e:
        logger.error("Background processing error for %s: %s", document_id, str(e))


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    organization_id: Optional[UUID] = Query(None, description="Target organization ID"),
    visibility: DocumentVisibility = Query(DocumentVisibility.PRIVATE, description="Document visibility"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a document file (PDF, DOCX, XLSX)."""
    # Validate format
    format_type = DocumentParser.get_format(file.filename or "")
    if not format_type:
        raise HTTPException(
            status_code=400,
            detail="Unsupported format. Use PDF, DOCX, or XLSX"
        )

    # Read file content
    content = await file.read()

    # Check size limit
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 50MB"
        )

    # Handle organization context
    org_id = None
    if organization_id:
        if not await permission_service.can_upload_to_organization(db, organization_id, current_user.id):
            raise HTTPException(status_code=403, detail="No permission to upload to this organization")

        quota_check = await organization_service.check_quota(
            db, organization_id,
            additional_documents=1,
            additional_storage=len(content)
        )
        if not quota_check["allowed"]:
            raise HTTPException(status_code=400, detail=quota_check["reason"])

        org_id = organization_id

    # Generate unique object name
    object_name = f"{current_user.id}/{uuid.uuid4()}_{file.filename}"

    # Store in MinIO
    try:
        await minio_service.upload_file(
            content,
            object_name,
            file.content_type or "application/octet-stream"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Create document record
    doc = Document(
        user_id=current_user.id,
        organization_id=org_id,
        filename=file.filename,
        file_path=object_name,
        file_size=len(content),
        format=format_type,
        status=DocumentStatus.PENDING,
        visibility=visibility,
        doc_metadata={}
    )
    db.add(doc)

    # Update organization usage stats if applicable
    if org_id:
        await organization_service.update_usage_stats(
            db, org_id,
            document_delta=1,
            storage_delta=len(content)
        )

    await db.commit()
    await db.refresh(doc)

    # Schedule background processing (replaces Celery .delay())
    background_tasks.add_task(
        _process_document_background,
        str(doc.id), object_name, format_type
    )

    return doc


@router.get("", response_model=DocumentList)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[DocumentStatus] = None,
    organization_id: Optional[UUID] = Query(None, description="Filter by organization"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List documents with optional organization filtering."""
    # Build base query
    if organization_id:
        # Get accessible documents query (includes membership check)
        base_query = await permission_service.get_accessible_documents_query(
            db, organization_id, current_user.id
        )
        if base_query is None:
            return DocumentList(items=[], total=0, skip=skip, limit=limit)
    else:
        base_query = select(Document).where(Document.user_id == current_user.id)

    # Build count query from the same base (avoids double permission lookup)
    count_base = base_query
    if status:
        count_base = count_base.where(Document.status == status)
    count_query = select(func.count()).select_from(count_base.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Build data query with pagination
    query = base_query
    if status:
        query = query.where(Document.status == status)
    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    documents = list(result.scalars().all())

    return DocumentList(
        items=documents,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific document by ID."""
    doc = await _get_document_with_access(doc_id, db, current_user)

    return doc


@router.get("/{doc_id}/status")
async def get_document_status(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document processing status."""
    doc = await _get_document_with_access(doc_id, db, current_user)

    return {
        "id": str(doc.id),
        "status": doc.status,
        "error_message": doc.error_message,
        "metadata": doc.doc_metadata,
        "organization_id": str(doc.organization_id) if doc.organization_id else None,
        "visibility": doc.visibility
    }


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a document and its file."""
    doc = await _get_document_with_access(doc_id, db, current_user, require_edit=True)

    # Store org info before deletion
    org_id = doc.organization_id
    file_size = doc.file_size or 0

    # Delete from MinIO
    try:
        await minio_service.delete_file(doc.file_path)
    except Exception as e:
        print(f"Warning: Failed to delete from MinIO: {e}")

    # Delete from DB (cascades to chunks)
    await db.delete(doc)

    # Update organization usage stats
    if org_id:
        await organization_service.update_usage_stats(
            db, org_id,
            document_delta=-1,
            storage_delta=-file_size
        )

    await db.commit()

    return {"message": "Document deleted successfully"}


@router.patch("/{doc_id}/visibility", response_model=DocumentResponse)
async def update_document_visibility(
    doc_id: str,
    data: DocumentVisibilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update document visibility (owner or admin only)."""
    doc = await _get_document_with_access(doc_id, db, current_user, require_edit=True)

    doc.visibility = data.visibility
    await db.commit()
    await db.refresh(doc)

    return doc


@router.post("/{doc_id}/access", response_model=DocumentAccessResponse, status_code=201)
async def grant_document_access(
    doc_id: str,
    data: DocumentAccessGrant,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Grant access to document for user or group."""
    doc = await _get_document_with_access(doc_id, db, current_user, require_edit=True)

    # Validate that exactly one of user_id or group_id is provided
    if (data.user_id is None and data.group_id is None) or \
       (data.user_id is not None and data.group_id is not None):
        raise HTTPException(status_code=400, detail="Provide either user_id or group_id, not both")

    # Grant access
    import uuid as uuid_module
    from datetime import datetime
    from app.models.models import DocumentAccess

    access = DocumentAccess(
        id=uuid_module.uuid4(),
        document_id=doc.id,
        user_id=data.user_id,
        group_id=data.group_id,
        access_level=data.access_level,
        granted_by_id=current_user.id,
        granted_at=datetime.utcnow()
    )
    db.add(access)
    await db.commit()
    await db.refresh(access)

    return access


@router.delete("/{doc_id}/access/{access_id}")
async def revoke_document_access(
    doc_id: str,
    access_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke access to document."""
    doc = await _get_document_with_access(doc_id, db, current_user, require_edit=True)

    # Find and delete access grant
    from app.models.models import DocumentAccess

    result = await db.execute(
        select(DocumentAccess).where(
            DocumentAccess.id == access_id,
            DocumentAccess.document_id == doc_id
        )
    )
    access = result.scalar_one_or_none()

    if not access:
        raise HTTPException(status_code=404, detail="Access grant not found")

    await db.delete(access)
    await db.commit()

    return {"message": "Access revoked successfully"}
