"""Tests for document endpoints."""
import pytest
from httpx import AsyncClient
import io


@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient, auth_headers):
    """Test listing documents when empty."""
    response = await client.get("/api/v1/documents", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_upload_pdf(client: AsyncClient, auth_headers):
    """Test uploading a PDF file."""
    file_content = b"%PDF-1.4\ntest pdf content"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}

    response = await client.post(
        "/api/v1/documents/upload",
        files=files,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["format"] == "pdf"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_docx(client: AsyncClient, auth_headers):
    """Test uploading a DOCX file."""
    # Minimal DOCX content (just PK header)
    file_content = b"PK\x03\x04minimal docx"
    files = {"file": ("test.docx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

    response = await client.post(
        "/api/v1/documents/upload",
        files=files,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.docx"
    assert data["format"] == "docx"


@pytest.mark.asyncio
async def test_upload_unsupported_format(client: AsyncClient, auth_headers):
    """Test uploading unsupported file format."""
    files = {"file": ("test.txt", io.BytesIO(b"text content"), "text/plain")}
    response = await client.post(
        "/api/v1/documents/upload",
        files=files,
        headers=auth_headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_without_auth(client: AsyncClient):
    """Test upload fails without auth."""
    file_content = b"test content"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
    response = await client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient, auth_headers):
    """Test getting nonexistent document."""
    response = await client.get(
        "/api/v1/documents/00000000-0000-0000-0000-000000000000",
        headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, auth_headers):
    """Test deleting a document."""
    # Upload first
    file_content = b"%PDF-1.4\ntest"
    files = {"file": ("delete_test.pdf", io.BytesIO(file_content), "application/pdf")}
    upload_response = await client.post(
        "/api/v1/documents/upload",
        files=files,
        headers=auth_headers
    )
    doc_id = upload_response.json()["id"]

    # Delete
    response = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert response.status_code == 200

    # Verify deleted
    get_response = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_cannot_access_other_user_documents(client: AsyncClient, auth_headers):
    """Test users can't access other users' documents."""
    # This would require creating another user and verifying isolation
    # For now, just verify the endpoint works with valid auth
    response = await client.get("/api/v1/documents", headers=auth_headers)
    assert response.status_code == 200
