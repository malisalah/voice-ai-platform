"""Request/response models for the Crawler Service."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CrawlJobStatus(str, Enum):
    """Status of a crawl job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CrawlStats(BaseModel):
    """Statistics from a crawl job."""

    pages_crawled: int = 0
    pages_failed: int = 0
    chunks_created: int = 0
    total_size_bytes: int = 0


class PageData(BaseModel):
    """Model for a single crawled page."""

    url: str
    title: Optional[str] = None
    content: str
    word_count: int = 0
    sentence_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChunkData(BaseModel):
    """Model for a single text chunk."""

    content: str
    page_url: str
    chunk_index: int
    word_count: int = 0
    sentence_count: int = 0
    overlap_context: Optional[str] = None


class CrawlJobResponse(BaseModel):
    """Response model for crawl job data."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    url: str
    status: CrawlJobStatus
    stats: Dict[str, Any]
    error_message: Optional[str] = None
    pages_crawled: int
    chunks_created: int
    created_at: datetime
    updated_at: datetime


class CrawlRequest(BaseModel):
    """Request model for triggering a crawl."""

    url: str = Field(..., pattern=r"^https?://")
    max_depth: Optional[int] = Field(default=1, ge=0, le=5)
    exclude_patterns: Optional[List[str]] = None


class CrawlResponse(BaseModel):
    """Response model for crawl trigger."""

    job_id: str
    status: CrawlJobStatus
    message: str


class ChunkListResponse(BaseModel):
    """Response model for chunk list."""

    chunks: List[ChunkData]
    total_chunks: int
    job_id: str
