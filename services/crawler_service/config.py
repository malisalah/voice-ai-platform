"""Pydantic settings for crawler-service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Crawler service configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Service configuration
    SERVICE_NAME: str = "crawler-service"
    SERVICE_PORT: int = Field(default=8004, description="Port to run the service on")
    ENVIRONMENT: str = Field(default="development")

    # Database configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/voiceai",
        description="PostgreSQL connection URL",
    )

    # Redis configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # Celery configuration
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL",
    )

    # Crawler configuration
    CRAWLER_DELAY_SECONDS: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Delay between requests in seconds"
    )
    CRAWLER_MAX_DEPTH: int = Field(default=2, ge=0, le=5, description="Max crawl depth")
    CRAWLER_MAX_PAGES: int = Field(default=100, ge=1, le=1000, description="Max pages to crawl")
    CRAWLER_USER_AGENT: str = Field(
        default="CrawlerService/1.0",
        description="User agent for crawling",
    )

    # Chunking configuration (PocketFlow)
    POCKETFLOW_CHUNK_SIZE: int = Field(
        default=200, ge=50, le=500, description="Max words per chunk"
    )
    POCKETFLOW_CHUNK_OVERLAP: int = Field(
        default=20, ge=5, le=100, description="Overlap words between chunks"
    )

    # Knowledge service URL for chunk storage
    KNOWLEDGE_SERVICE_URL: str = Field(
        default="http://knowledge-service:8003",
        description="URL of the knowledge service",
    )


settings = Settings()
