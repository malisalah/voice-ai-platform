"""Tenant schema and related models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, IDMixin, TenantMixin, TimestampMixin


class Tenant(Base, IDMixin, TenantMixin, TimestampMixin):
    """SQLAlchemy model for tenant data."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(nullable=False)
    website_url: Mapped[Optional[str]] = mapped_column(default=None)
    api_key_hash: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    default_llm_model: Mapped[Optional[str]] = mapped_column(default=None)


class TenantCreate(BaseModel):
    """Request model for creating a tenant."""

    name: str = Field(..., min_length=1, max_length=255)
    website_url: Optional[str] = Field(None, pattern=r"^https?://")
    default_llm_model: Optional[str] = None


class TenantUpdate(BaseModel):
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


class APIKey(BaseModel):
    """API key model."""

    id: str
    tenant_id: str
    key_hash: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool


class APIKeyCreate(BaseModel):
    """Request model for creating an API key."""

    name: str = Field(..., min_length=1, max_length=100)
    expires_days: Optional[int] = Field(None, ge=1, le=365)
