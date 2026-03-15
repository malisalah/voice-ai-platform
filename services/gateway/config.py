"""Pydantic Settings for gateway service."""

import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """Gateway service configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Service configuration
    SERVICE_NAME: str = "gateway"
    SERVICE_PORT: int = 8000
    ENVIRONMENT: str = Field(default="development")

    # JWT configuration
    JWT_SECRET_KEY: str = Field(default="")
    JWT_ALGORITHM: str = Field(default="HS256")
    TOKEN_EXPIRY_MINUTES: int = Field(default=60)

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)

    # Backend service URLs
    TENANT_SERVICE_URL: str = Field(default="http://tenant-service:8005")
    VOICE_SERVICE_URL: str = Field(default="http://voice-service:8001")
    LLM_SERVICE_URL: str = Field(default="http://llm-service:8002")
    KNOWLEDGE_SERVICE_URL: str = Field(default="http://knowledge-service:8003")
    CRAWLER_SERVICE_URL: str = Field(default="http://crawler-service:8004")

    # CORS configuration
    GATEWAY_ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8006"
    )

    # Redis configuration
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")

    @property
    def allowed_origins(self) -> List[str]:
        """Parse allowed origins from comma-separated string."""
        return [
            origin.strip()
            for origin in self.GATEWAY_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


# Create global settings instance
settings = GatewaySettings()
