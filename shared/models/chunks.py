"""Chunk schema for storing document chunks."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, IDMixin, TenantMixin, TimestampMixin


class Chunk(Base, IDMixin, TenantMixin, TimestampMixin):
    """SQLAlchemy model for document chunks."""

    __tablename__ = "chunks"

    url: Mapped[str] = mapped_column(nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    chunk_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    embedding_hash: Mapped[Optional[str]] = mapped_column(default=None)
    word_count: Mapped[int] = mapped_column(default=0)
    sentence_count: Mapped[int] = mapped_column(default=0)


class ChunkResponse(BaseModel):
    """Response model for chunk data."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    url: str
    chunk_index: int
    content: str
    chunk_metadata: Dict[str, Any]
    word_count: int
    sentence_count: int
    created_at: datetime


class ChunkSearchRequest(BaseModel):
    """Request model for chunk search."""

    query: str = Field(..., min_length=1)
    tenant_id: str
    top_k: int = Field(default=5, ge=1, le=50)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ChunkSearchResponse(BaseModel):
    """Response model for chunk search results."""

    query: str
    results: list[ChunkResponse]
    total_count: int
    min_score: float
    max_score: float
