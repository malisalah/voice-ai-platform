"""Pydantic schemas for gateway service."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GatewayResponse(BaseModel):
    """Standard gateway response model."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthCheck(BaseModel):
    """Health check status for a downstream service."""

    service: str
    status: str  # "healthy", "unhealthy", "degraded"
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class HealthStatus(BaseModel):
    """Overall health status response."""

    status: str  # "healthy", "degraded", "unhealthy"
    services: List[HealthCheck]
    timestamp: datetime


class RateLimitStatus(BaseModel):
    """Rate limit status response."""

    tenant_id: str
    endpoint: str
    limit: int
    remaining: int
    reset_at: datetime


class TokenExchangeRequest(BaseModel):
    """Request to exchange API key for JWT token."""

    api_key: str = Field(..., min_length=64, max_length=64)


class TokenExchangeResponse(BaseModel):
    """Response with JWT token."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class TokenVerifyRequest(BaseModel):
    """Request to verify a JWT token."""

    token: str


class TokenVerifyResponse(BaseModel):
    """Response with token validity."""

    valid: bool
    tenant_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


class ProxyRequest(BaseModel):
    """Internal proxy request model."""

    method: str
    path: str
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None


class ProxyResponse(BaseModel):
    """Internal proxy response model."""

    status_code: int
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None
    raw_body: Optional[bytes] = None
