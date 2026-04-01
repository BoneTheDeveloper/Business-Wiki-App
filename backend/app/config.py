"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    SUPABASE_URL: str = "http://127.0.0.1:54321"
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Database (default: local Supabase stack)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "documents"
    MINIO_SECURE: bool = False

    # OpenAI
    OPENAI_API_KEY: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
