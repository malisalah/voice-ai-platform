"""Pydantic settings for tenant-service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Tenant service configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Service configuration
    SERVICE_NAME: str = "tenant-service"
    SERVICE_PORT: int = Field(default=8005, description="Port to run the service on")
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

    # JWT configuration
    PLATFORM_SECRET_KEY: str = Field(
        default="changeme",
        description="Secret key for JWT signing",
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRY_MINUTES: int = Field(default=60, ge=1, le=1440)

    # Tenant defaults
    DEFAULT_TENANT_NAME: str = Field(default="Default Tenant")
    DEFAULT_LLM_MODEL: str = Field(default="qwen3.5:cloud")

    # Security
    API_KEY_LENGTH: int = Field(default=64, description="Length of generated API keys")


settings = Settings()
