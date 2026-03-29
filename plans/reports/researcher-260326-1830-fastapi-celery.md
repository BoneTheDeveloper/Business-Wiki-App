# FastAPI + Celery Document Processing Pipeline Research

## Executive Summary
FastAPI + Celery + Redis is a proven architecture for document processing microservices with high performance, scalability, and real-time capabilities.

---

## 1. FastAPI Project Structure

### Recommended Structure
```
app/
├── main.py                 # FastAPI app entry point
├── config.py               # Configuration management
├── dependencies.py         # Shared dependencies (DB session, auth)
├── auth/
│   ├── routes.py          # Auth endpoints
│   ├── schemas.py         # Auth schemas
│   └── security.py        # JWT, password hashing
├── api/
│   ├── v1/
│   │   ├── routes/
│   │   │   ├── documents.py
│   │   │   ├── users.py
│   │   │   └── processing.py
│   │   └── deps.py        # API dependencies
├── services/
│   ├── document_service.py
│   ├── celery_tasks.py
│   └── parsing.py         # Document parsers
├── models/
│   ├── database.py
│   ├── schemas.py         # Pydantic models
│   └── models.py          # SQLAlchemy models
├── celery_app.py
└── utils/
    ├── rate_limiter.py
    ├── file_handler.py
    └── websocket.py
```

### Key Patterns
- **Modular API**: Separate routes by domain (documents, users, processing)
- **Dependency Injection**: Centralized dependencies in `dependencies.py`
- **Configuration**: Environment-based config with validation
- **Separation of Concerns**: Service layer for business logic, routes for HTTP handling

---

## 2. Celery Task Queues with Redis

### Celery Configuration
```python
# celery_app.py
from celery import Celery
from kombu import Queue, Exchange

celery_app = Celery(
    'business_wiki',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
    include=['app.services.celery_tasks'],
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300  # Warn at 55 minutes
)

# Task routing for priority queues
celery_app.conf.task_routes = {
    'app.services.celery_tasks.*': {'queue': 'default'},
    'app.services.celery_tasks.high_priority': {'queue': 'high_priority'},
    'app.services.celery_tasks.low_priority': {'queue': 'low_priority'},
}

# Concurrency configuration
celery_app.conf.worker_prefetch_multiplier = 4
celery_app.conf.worker_concurrency = 4
```

### Document Processing Tasks
```python
# celery_tasks.py
from celery import shared_task
from app.services.parsing import parse_document

@shared_task(bind=True, name='process_document')
def process_document(self, document_id, user_id, file_path, format_type):
    """Process document with progress tracking"""
    task_id = self.request.id

    try:
        # Extract metadata
        metadata = extract_metadata(file_path, format_type)

        # Parse document
        content = parse_document(file_path, format_type)

        # Store results in database
        document = Document.objects.create(
            id=document_id,
            user_id=user_id,
            file_path=file_path,
            format=format_type,
            metadata=metadata,
            status='processing',
            task_id=task_id
        )

        # Process text extraction (CPU intensive)
        text = extract_text(file_path, format_type)
        document.text_content = text
        document.status = 'completed'
        document.save()

        return {
            'document_id': document_id,
            'status': 'completed',
            'task_id': task_id
        }

    except Exception as e:
        document.status = 'failed'
        document.error_message = str(e)
        document.save()
        raise
```

### Queue Strategy
- **Default queue**: Standard processing (balance speed/quality)
- **High priority queue**: Urgent documents, near-time requirements
- **Low priority queue**: Batch processing, offline cleanup

---

## 3. Async File Processing

### Asynchronous Upload Pattern
```python
# routes/documents.py
from fastapi import UploadFile, File
from app.services.celery_tasks import process_document

@router.post('/documents/upload')
async def upload_document(
    file: UploadFile = File(...),
    format_type: str = None,
    priority: str = 'normal'
):
    """Async upload with immediate response"""
    file_id = str(uuid.uuid4())
    file_path = f"uploads/{file_id}_{file.filename}"

    # Save file immediately
    await save_file(file, file_path)

    # Dispatch to Celery queue based on priority
    if priority == 'high':
        task = process_document.delay(file_id, current_user.id, file_path, format_type, priority)
    else:
        task = process_document.apply_async(
            args=[file_id, current_user.id, file_path, format_type],
            priority=2 if priority == 'normal' else 1
        )

    return {
        'file_id': file_id,
        'status': 'queued',
        'task_id': task.id,
        'status_url': f"/api/v1/documents/{file_id}/status"
    }
```

### Background Cleanup Task
```python
@shared_task(name='cleanup_stale_files')
def cleanup_stale_files():
    """Remove files older than 7 days not linked to documents"""
    from datetime import datetime, timedelta
    from app.models import Document

    cutoff = datetime.now() - timedelta(days=7)
    stale_files = Document.objects.filter(
        status='completed',
        created_at__lt=cutoff
    )

    for doc in stale_files:
        if not os.path.exists(doc.file_path):
            doc.delete()
        elif doc.file_size > 0:  # Already processed
            os.remove(doc.file_path)
            doc.delete()
```

---

## 4. JWT Authentication with RBAC

### Security Configuration
```python
# auth/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')

# Secret key in production (use environment variable)
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
```

### RBAC Middleware
```python
# dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.auth.security import verify_token
from app.models import User, Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')

async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get('sub')
    if user_id is None:
        raise credentials_exception

    user = await User.get(id=user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail='Inactive user')
    return current_user

async def require_role(role: Role):
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'Role {role} required'
            )
        return current_user

    return role_checker

# Usage in routes
@router.get('/documents', dependencies=[Depends(require_role(Role.ADMIN))])
def list_documents():
    pass
```

---

## 5. Rate Limiting Strategies

### Token Bucket Implementation
```python
# utils/rate_limiter.py
from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Apply rate limiting to routes
@router.post('/upload')
@limiter.limit("10/minute")  # 10 uploads per minute
async def upload_document(request: Request, ...):
    pass

# Per-user rate limiting
@router.post('/upload')
async def upload_document(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    # Get user-specific rate limit
    limit = f"{get_user_quota(current_user.role)}/hour"
    await limiter.check_request_limit(request, get_remote_address, limit)
    pass

# IP-based blocking
@limiter.exempt  # Skip rate limiting for certain endpoints
@router.get('/health')
def health_check():
    pass
```

### Alternative: Redis-based Rate Limiter
```python
# utils/rate_limiter_redis.py
import redis
from datetime import datetime, timedelta
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

async def check_rate_limit(key: str, max_requests: int, window: int):
    current = redis_client.incr(key)
    if current == 1:
        redis_client.expire(key, window)
    if current > max_requests:
        raise HTTPException(
            status_code=429,
            detail=f'Max {max_requests} requests per {window} seconds'
        )

def rate_limit(max_requests: int, window: int = 60):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            ip = request.client.host
            key = f'rate_limit:{ip}:{request.url.path}'
            await check_rate_limit(key, max_requests, window)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
```

---

## 6. WebSocket Support in FastAPI

### WebSocket Document Status
```python
# utils/websocket.py
from fastapi import WebSocket
from typing import Dict

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, document_id: str):
        await websocket.accept()
        self.active_connections[document_id] = websocket

    def disconnect(self, document_id: str):
        if document_id in self.active_connections:
            del self.active_connections[document_id]

    async def send_status(self, document_id: str, status: dict):
        if document_id in self.active_connections:
            await self.active_connections[document_id].send_json(status)

manager = ConnectionManager()

# In routes
@router.websocket("/ws/document/{document_id}")
async def websocket_endpoint(websocket: WebSocket, document_id: str):
    await manager.connect(websocket, document_id)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Handle client messages
    except Exception as e:
        manager.disconnect(document_id)
    finally:
        manager.disconnect(document_id)
```

### Integration with Celery
```python
# In celery_tasks.py
from app.utils.websocket import manager

@shared_task
def process_document(document_id, ...):
    # Send status updates via WebSocket
    manager.send_status(document_id, {'status': 'processing', 'progress': 10})

    # Process...
    manager.send_status(document_id, {'status': 'processing', 'progress': 50})

    # Complete
    manager.send_status(document_id, {'status': 'completed', 'progress': 100})

# Client-side connection
import asyncio
import websockets

async def watch_document_progress(document_id: str):
    uri = f"ws://localhost:8000/ws/document/{document_id}"
    async with websockets.connect(uri) as websocket:
        while True:
            data = await websocket.recv()
            status = json.loads(data)
            print(f"Status: {status}")
```

---

## 7. Document Parsing Libraries

### Recommended Stack
```python
# services/parsing.py
import os
from typing import Dict, Any
from docx import Document as DocxDocument
from PyPDF2 import PdfReader
from openpyxl import load_workbook

class DocumentParser:
    SUPPORTED_FORMATS = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }

    @classmethod
    def parse(cls, file_path: str, format_type: str) -> Dict[str, Any]:
        if format_type not in cls.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format_type}")

        file_size = os.path.getsize(file_path)
        metadata = cls._extract_metadata(file_path, format_type)

        content = cls._extract_content(file_path, format_type)

        return {
            'format': format_type,
            'file_size': file_size,
            'metadata': metadata,
            'content': content
        }

    @classmethod
    def _extract_metadata(cls, file_path: str, format_type: str) -> Dict[str, Any]:
        """Extract document metadata"""
        metadata = {'format': format_type}

        if format_type == 'docx':
            doc = DocxDocument(file_path)
            metadata.update({
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'created': doc.metadata.get('creation_date', ''),
                'words': sum(len(p.text.split()) for p in doc.paragraphs)
            })

        elif format_type == 'pdf':
            reader = PdfReader(file_path)
            metadata.update({
                'pages': len(reader.pages),
                'author': reader.metadata.author if reader.metadata else '',
                'creator': reader.metadata.creator if reader.metadata else ''
            })

        elif format_type == 'xlsx':
            wb = load_workbook(file_path, read_only=True)
            metadata.update({
                'sheets': len(wb.sheetnames),
                'last_sheet': wb.sheetnames[-1]
            })

        return metadata

    @classmethod
    def _extract_content(cls, file_path: str, format_type: str) -> str:
        """Extract text content"""
        if format_type == 'docx':
            doc = DocxDocument(file_path)
            return '\n'.join(p.text for p in doc.paragraphs)

        elif format_type == 'pdf':
            reader = PdfReader(file_path)
            text = []
            for page in reader.pages:
                text.append(page.extract_text())
            return '\n'.join(text)

        elif format_type == 'xlsx':
            wb = load_workbook(file_path, read_only=True)
            result = []
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    result.append('\t'.join(str(cell) if cell is not None else '' for cell in row))
            return '\n'.join(result)

        return ""
```

### Performance Optimization
```python
# Use memory-efficient parsing
import memory_profiler

@memory_profiler.profile
def process_large_file(file_path: str, format_type: str):
    """Profile and optimize memory usage"""
    pass

# Process in chunks for large files
class ChunkedParser:
    @staticmethod
    def process_in_chunks(file_path: str, chunk_size: int = 1000):
        """Process files in chunks to reduce memory usage"""
        with open(file_path, 'r', encoding='utf-8') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

# Async I/O for file operations
import aiofiles
from aiofiles.os import stat

async def async_save_file(file: UploadFile, file_path: str):
    """Async file save"""
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
```

---

## Recommendations Summary

### Architecture Pattern
- **Separate services**: FastAPI for HTTP API, Celery for background processing
- **Redis as broker**: Efficient task queue with support for priorities
- **WebSocket for status**: Real-time progress updates to clients

### Authentication
- **JWT tokens**: Stateless, scalable authentication
- **RBAC roles**: ADMIN, EDITOR, USER with granular permissions
- **Rate limiting**: IP-based and user-based to prevent abuse

### Performance
- **Async file operations**: aiofiles for non-blocking I/O
- **Chunked processing**: For large documents to prevent memory issues
- **Worker concurrency**: Adjust based on CPU resources (default: 4 workers)

### Document Parsing
- **python-docx**: For .docx files (Word)
- **PyPDF2**: For PDF files
- **openpyxl**: For Excel files (.xlsx)
- **Metadata extraction**: Preserve document properties

### Deployment
- **Celery workers**: Run separate processes (recommended: 1-4 workers)
- **Redis**: Required for broker and result backend
- **Worker health**: Use Celery Flower for monitoring

---

## Unresolved Questions

1. **Document size limits**: What's the maximum file size to support? This affects chunking strategy
2. **Processing time expectations**: What SLA for document processing? Affects worker concurrency
3. **Document types**: Are there other formats besides PDF, DOCX, XLSX?
4. **Authentication scope**: Should role-based access be document-level or system-level?
5. **WebSocket usage**: Will all users need real-time status updates, or just admins?
6. **Redundancy**: Should document processing be replicated for fault tolerance?
7. **Queue persistence**: Is disk-based persistence required for failed tasks?

---

## Resources

### Official Documentation
- FastAPI: https://fastapi.tiangolo.com/
- Celery: https://docs.celeryq.dev/
- Redis: https://redis.io/docs/
- JWT: https://jwt.io/

### Best Practices
- FastAPI microservices patterns
- Celery Redis queue setup
- Async Python patterns
- WebSocket real-time communication
