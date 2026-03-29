# Phase 03 - Document Service

**Priority:** P0 | **Duration:** 3 days | **Status:** Pending

## Overview

Implement document upload, MinIO storage integration, and file parsing for PDF, DOCX, XLSX formats.

## Key Insights

- MinIO for S3-compatible object storage
- Chunked upload for large files (50MB limit)
- Async file processing via Celery
- Multi-format parsing: PyPDF2, python-docx, openpyxl

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  POST /api/v1/documents/upload                              │
│  GET  /api/v1/documents                                     │
│  GET  /api/v1/documents/{id}                                │
│  DEL  /api/v1/documents/{id}                                │
│  GET  /api/v1/documents/{id}/status                         │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  MinIO           │ │  PostgreSQL      │ │  Celery Task     │
│  Store files     │ │  Document meta   │ │  Parse async     │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

## Requirements

### Functional
- Upload PDF, DOCX, XLSX files (max 50MB)
- Store files in MinIO bucket
- Track upload progress
- Parse and extract text content
- Store metadata (pages, word count, etc.)

### Non-Functional
- Upload timeout: 5 minutes
- Concurrent uploads: 5 per user
- Parse queue priority levels

## Related Files

**Create:**
- `backend/app/services/minio_service.py` - MinIO client
- `backend/app/services/document_service.py` - Upload logic
- `backend/app/services/parsing.py` - File parsers
- `backend/app/api/v1/routes/documents.py` - Endpoints

## Implementation Steps

### 1. MinIO Service

```python
# backend/app/services/minio_service.py
from minio import Minio
from minio.error import S3Error
from app.config import settings
import io

class MinioService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        if not self.client.bucket_exists(settings.MINIO_BUCKET):
            self.client.make_bucket(settings.MINIO_BUCKET)

    async def upload_file(self, file_data: bytes, object_name: str, content_type: str) -> str:
        """Upload file to MinIO, return object path"""
        self.client.put_object(
            settings.MINIO_BUCKET,
            object_name,
            data=io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type
        )
        return f"{settings.MINIO_BUCKET}/{object_name}"

    async def get_file(self, object_name: str) -> bytes:
        """Download file from MinIO"""
        response = self.client.get_object(settings.MINIO_BUCKET, object_name)
        return response.read()

    async def delete_file(self, object_name: str) -> bool:
        """Delete file from MinIO"""
        self.client.remove_object(settings.MINIO_BUCKET, object_name)
        return True

minio_service = MinioService()
```

### 2. Document Parsing

```python
# backend/app/services/parsing.py
from typing import Dict, Any, Optional
import os
from PyPDF2 import PdfReader
from docx import Document as DocxDocument
from openpyxl import load_workbook
import tempfile

class DocumentParser:
    @staticmethod
    def get_format(filename: str) -> Optional[str]:
        ext = filename.lower().split('.')[-1]
        return ext if ext in ['pdf', 'docx', 'xlsx'] else None

    @staticmethod
    def parse(file_path: str, format_type: str) -> Dict[str, Any]:
        parser_map = {
            'pdf': DocumentParser._parse_pdf,
            'docx': DocumentParser._parse_docx,
            'xlsx': DocumentParser._parse_xlsx
        }
        return parser_map[format_type](file_path)

    @staticmethod
    def _parse_pdf(file_path: str) -> Dict[str, Any]:
        reader = PdfReader(file_path)
        text_content = []
        for page in reader.pages:
            text_content.append(page.extract_text() or "")

        return {
            'text': '\n'.join(text_content),
            'metadata': {
                'pages': len(reader.pages),
                'author': reader.metadata.author if reader.metadata else None,
                'title': reader.metadata.title if reader.metadata else None,
            }
        }

    @staticmethod
    def _parse_docx(file_path: str) -> Dict[str, Any]:
        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

        return {
            'text': '\n'.join(paragraphs),
            'metadata': {
                'paragraphs': len(paragraphs),
                'words': sum(len(p.split()) for p in paragraphs),
                'title': doc.core_properties.title,
                'author': doc.core_properties.author,
            }
        }

    @staticmethod
    def _parse_xlsx(file_path: str) -> Dict[str, Any]:
        wb = load_workbook(file_path, read_only=True, data_only=True)
        rows = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                row_text = '\t'.join(str(cell) if cell else '' for cell in row)
                if row_text.strip():
                    rows.append(row_text)

        return {
            'text': '\n'.join(rows),
            'metadata': {
                'sheets': len(wb.sheetnames),
                'sheet_names': wb.sheetnames,
            }
        }
```

### 3. Document Routes

```python
# backend/app/api/v1/routes/documents.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
import uuid
from app.models.database import get_db
from app.models.models import Document, DocumentStatus, User
from app.models.schemas import DocumentResponse, DocumentList
from app.dependencies import get_current_user
from app.services.minio_service import minio_service
from app.services.parsing import DocumentParser
from app.services.celery_tasks import process_document

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate format
    format_type = DocumentParser.get_format(file.filename)
    if not format_type:
        raise HTTPException(400, "Unsupported format. Use PDF, DOCX, or XLSX")

    # Check size (50MB limit)
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "File too large. Max 50MB")

    # Store in MinIO
    object_name = f"{current_user.id}/{uuid.uuid4()}_{file.filename}"
    file_path = await minio_service.upload_file(
        content, object_name, file.content_type
    )

    # Create document record
    doc = Document(
        user_id=current_user.id,
        filename=file.filename,
        file_path=object_name,
        file_size=len(content),
        format=format_type,
        status=DocumentStatus.PENDING
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Queue processing task
    process_document.delay(str(doc.id), object_name, format_type)

    return doc

@router.get("", response_model=DocumentList)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[DocumentStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Document).where(Document.user_id == current_user.id)

    if status:
        query = query.where(Document.status == status)

    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    documents = result.scalars().all()

    # Get total count
    count_query = select(func.count(Document.id)).where(Document.user_id == current_user.id)
    total = (await db.execute(count_query)).scalar()

    return DocumentList(items=documents, total=total, skip=skip, limit=limit)

@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.user_id == current_user.id
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(404, "Document not found")

    return doc

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.user_id == current_user.id
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(404, "Document not found")

    # Delete from MinIO
    await minio_service.delete_file(doc.file_path)

    # Delete from DB (cascades to chunks)
    await db.delete(doc)
    await db.commit()

    return {"message": "Document deleted"}
```

### 4. Celery Tasks

```python
# backend/app/services/celery_tasks.py
from celery import shared_task
from app.services.parsing import DocumentParser
from app.services.minio_service import minio_service
import tempfile
import os

@shared_task(name="process_document", bind=True)
def process_document(self, document_id: str, file_path: str, format_type: str):
    """Process document: download, parse, chunk, embed"""
    from app.models.database import AsyncSessionLocal
    from app.models.models import Document, DocumentStatus, DocumentChunk
    from app.services.rag_service import RAGService
    import asyncio

    async def _process():
        async with AsyncSessionLocal() as db:
            # Get document
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                return {"error": "Document not found"}

            # Update status
            doc.status = DocumentStatus.PROCESSING
            await db.commit()

            try:
                # Download file
                content = await minio_service.get_file(file_path)

                # Save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format_type}") as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name

                # Parse
                parsed = DocumentParser.parse(tmp_path, format_type)

                # Update metadata
                doc.metadata = parsed['metadata']

                # Chunk and embed
                rag = RAGService()
                chunks = rag.chunk_text(parsed['text'], doc.metadata)

                # Store chunks with embeddings
                for i, chunk in enumerate(chunks):
                    embedding = await rag.embed(chunk['content'])
                    db_chunk = DocumentChunk(
                        document_id=doc.id,
                        content=chunk['content'],
                        embedding=embedding,
                        chunk_index=i,
                        metadata=chunk.get('metadata', {})
                    )
                    db.add(db_chunk)

                # Cleanup
                os.unlink(tmp_path)

                # Mark complete
                doc.status = DocumentStatus.COMPLETED
                await db.commit()

                return {"document_id": document_id, "status": "completed"}

            except Exception as e:
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)
                await db.commit()
                raise

    return asyncio.run(_process())
```

## Todo List

- [ ] Create minio_service.py
- [ ] Create parsing.py with PDF/DOCX/XLSX parsers
- [ ] Create document routes (upload, list, get, delete)
- [ ] Create celery_tasks.py with process_document task
- [ ] Update main.py with document routes
- [ ] Add file size validation
- [ ] Add format validation
- [ ] Test: Upload PDF returns 201
- [ ] Test: List documents returns user's docs only
- [ ] Test: Delete removes from MinIO and DB
- [ ] Test: Celery task processes document

## Success Criteria

1. User can upload PDF/DOCX/XLSX files
2. Files stored in MinIO bucket
3. Document metadata extracted correctly
4. Processing status tracked in real-time
5. Delete removes file and all chunks

## Next Steps

- Phase 04: RAG pipeline (chunking, embeddings, vector search)
