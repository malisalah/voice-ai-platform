"""Pydantic schemas for request/response models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TenantCreateRequest(BaseModel):
    """Request model for creating a tenant."""

    name: str = Field(..., min_length=1, max_length=255)
    website_url: Optional[str] = Field(None, pattern=r"^https?://")
    default_llm_model: Optional[str] = None


class TenantUpdateRequest(BaseModel):
    """Request model for updating a tenant."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    website_url: Optional[str] = Field(None, pattern=r"^https?://")
    is_active: Optional[bool] = None
    default_llm_model: Optional[str] = None


class TenantResponse(BaseModel):
    """Response model for tenant data."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    website_url: Optional[str] = None
    is_active: bool
    default_llm_model: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class APIKeyCreateRequest(BaseModel):
    """Request model for creating an API key."""

    name: str = Field(..., min_length=1, max_length=100)
    expires_days: Optional[int] = Field(None, ge=1, le=365)


class APIKeyResponse(BaseModel):
    """Response model for API key data."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool


class APIKeyCreateResponse(BaseModel):
    """Response model for API key creation (includes plain key)."""

    id: str
    tenant_id: str
    name: str
    key: str  # Plain key - returned ONLY once at creation
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool


class ListResponse(BaseModel):
    """Generic list response model."""

    items: list
    total: int
    limit: int
    offset: int


class MessageResponse(BaseModel):
    """Simple message response model."""

    message: str
