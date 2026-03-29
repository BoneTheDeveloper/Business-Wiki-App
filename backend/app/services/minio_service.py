"""MinIO object storage service for document files."""
import io
from typing import Optional
from minio import Minio
from minio.error import S3Error
from app.config import settings


class MinioService:
    """MinIO client for file storage operations."""

    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(settings.MINIO_BUCKET):
                self.client.make_bucket(settings.MINIO_BUCKET)
        except S3Error as e:
            # Log error but don't fail init - bucket may already exist
            print(f"MinIO bucket check error: {e}")

    async def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str
    ) -> str:
        """Upload file to MinIO, return object path."""
        try:
            self.client.put_object(
                settings.MINIO_BUCKET,
                object_name,
                data=io.BytesIO(file_data),
                length=len(file_data),
                content_type=content_type
            )
            return f"{settings.MINIO_BUCKET}/{object_name}"
        except S3Error as e:
            raise RuntimeError(f"Failed to upload file: {e}")

    async def get_file(self, object_name: str) -> bytes:
        """Download file from MinIO."""
        try:
            response = self.client.get_object(settings.MINIO_BUCKET, object_name)
            return response.read()
        except S3Error as e:
            raise RuntimeError(f"Failed to get file: {e}")

    async def delete_file(self, object_name: str) -> bool:
        """Delete file from MinIO."""
        try:
            self.client.remove_object(settings.MINIO_BUCKET, object_name)
            return True
        except S3Error as e:
            print(f"Failed to delete file: {e}")
            return False

    async def file_exists(self, object_name: str) -> bool:
        """Check if file exists in MinIO."""
        try:
            self.client.stat_object(settings.MINIO_BUCKET, object_name)
            return True
        except S3Error:
            return False


# Singleton instance
minio_service = MinioService()
