"""Tests for document endpoints."""
import pytest
import io
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_list_documents_empty(auth_client: AsyncClient):
    """Test listing documents when empty."""
    response = await auth_client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_upload_pdf(auth_client: AsyncClient):
    """Test uploading a PDF file."""
    with patch("app.api.v1.routes.documents.minio_service") as mock_minio, \
         patch("app.services.celery_tasks.process_document_task") as mock_task:
        mock_minio.upload_file = AsyncMock()
        mock_task.delay.return_value.id = "test-task-id"

        file_content = b"%PDF-1.4\ntest pdf content"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}

        response = await auth_client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["format"] == "pdf"
        assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_docx(auth_client: AsyncClient):
    """Test uploading a DOCX file."""
    with patch("app.api.v1.routes.documents.minio_service") as mock_minio, \
         patch("app.services.celery_tasks.process_document_task") as mock_task:
        mock_minio.upload_file = AsyncMock()
        mock_task.delay.return_value.id = "test-task-id"

        file_content = b"PK\x03\x04minimal docx"
        files = {"file": ("test.docx", io.BytesIO(file_content),
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

        response = await auth_client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.docx"
        assert data["format"] == "docx"


@pytest.mark.asyncio
async def test_upload_unsupported_format(auth_client: AsyncClient):
    """Test uploading unsupported file format returns 400."""
    files = {"file": ("test.txt", io.BytesIO(b"text content"), "text/plain")}
    response = await auth_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_without_auth(client: AsyncClient):
    """Test upload fails without auth."""
    file_content = b"test content"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
    response = await client.post("/api/v1/documents/upload", files=files)
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_document_not_found(auth_client: AsyncClient):
    """Test getting nonexistent document."""
    response = await auth_client.get(
        "/api/v1/documents/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document(auth_client: AsyncClient):
    """Test uploading then deleting a document."""
    with patch("app.api.v1.routes.documents.minio_service") as mock_minio, \
         patch("app.services.celery_tasks.process_document_task") as mock_task:
        mock_minio.upload_file = AsyncMock()
        mock_minio.delete_file = AsyncMock()
        mock_task.delay.return_value.id = "test-task-id"

        # Upload first
        file_content = b"%PDF-1.4\ntest"
        files = {"file": ("delete_test.pdf", io.BytesIO(file_content), "application/pdf")}
        upload_resp = await auth_client.post("/api/v1/documents/upload", files=files)
        assert upload_resp.status_code == 201
        doc_id = upload_resp.json()["id"]

        # Delete
        response = await auth_client.delete(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 200

        # Verify deleted
        get_resp = await auth_client.get(f"/api/v1/documents/{doc_id}")
        assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_documents_list_returns_own_only(auth_client: AsyncClient):
    """Test documents list returns only user's own docs."""
    response = await auth_client.get("/api/v1/documents")
    assert response.status_code == 200
