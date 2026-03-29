"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql://wiki:wiki_secret@localhost:5432/wiki_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "documents"
    MINIO_SECURE: bool = False

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    # OpenAI
    OPENAI_API_KEY: str = ""

    # OAuth Configuration
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/oauth/callback"
    APP_URL: str = "http://localhost:5173"
    OAUTH_AUTO_REGISTER: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
