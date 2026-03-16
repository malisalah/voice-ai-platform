"""Crawl job status and listing endpoints."""

from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    CrawlJobResponse,
    CrawlJobStatus,
    CrawlStats,
)

# Import the in-memory storage from the crawl router
from app.routers.crawl import _crawl_jobs

router = APIRouter(prefix="/crawl", tags=["crawl-status"])


@router.get("/{job_id}/status", response_model=CrawlJobResponse)
async def get_job_status(job_id: str):
    """Get the status of a specific crawl job."""
    job_data = _crawl_jobs.get(job_id)

    if not job_data:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Crawl job {job_id} not found",
        )

    return CrawlJobResponse(
        id=job_id,
        tenant_id=job_data.get("tenant_id", "unknown"),
        url=job_data["url"],
        status=job_data["status"],
        stats=job_data.get("stats", {}),
        error_message=job_data.get("error_message"),
        pages_crawled=job_data.get("pages_crawled", 0),
        chunks_created=job_data.get("chunks_created", 0),
        created_at=job_data["created_at"],
        updated_at=job_data.get("updated_at", job_data["created_at"]),
    )


@router.get("", response_model=list[CrawlJobResponse])
async def list_jobs(
    tenant_id: str = Query(..., description="Tenant ID to filter jobs"),
    status: CrawlJobStatus | None = Query(None, description="Filter by status"),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all crawl jobs for a tenant."""
    from sqlalchemy import select

    async with get_session() as session:
        repo = CrawlJobRepository(session)

        stmt = select(CrawlJob).where(
            CrawlJob.tenant_id == tenant_id
        )
        if status:
            stmt = stmt.where(CrawlJob.status == status)

        stmt = stmt.order_by(CrawlJob.created_at.desc()).limit(limit).offset(offset)

        result = await session.execute(stmt)
        jobs = result.scalars().all()

    return [
        CrawlJobResponse(
            id=job.id,
            tenant_id=job.tenant_id,
            url=job.url,
            status=job.status,
            stats=job.stats or {},
            error_message=job.error_message,
            pages_crawled=job.pages_crawled,
            chunks_created=job.chunks_created,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        for job in jobs
    ]
