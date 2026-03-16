"""Database repository for crawl job management."""

from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.base import get_session
from shared.models.crawl import CrawlJob, CrawlJobStatus


class CrawlJobRepository:
    """Async repository for CrawlJob CRUD operations."""

    def __init__(self, session: AsyncSession | None = None):
        self.session = session

    async def create_job(
        self,
        tenant_id: str,
        url: str,
        max_depth: int = 1,
        exclude_patterns: list[str] | None = None,
    ) -> CrawlJob:
        """Create a new crawl job."""
        job = CrawlJob(
            tenant_id=tenant_id,
            url=url,
            status=CrawlJobStatus.PENDING,
            stats={
                "max_depth": max_depth,
                "exclude_patterns": exclude_patterns or [],
            },
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_job(self, job_id: str) -> Optional[CrawlJob]:
        """Get a crawl job by ID."""
        result = await self.session.get(CrawlJob, job_id)
        return result

    async def get_job_by_tenant(
        self, tenant_id: str, job_id: str
    ) -> Optional[CrawlJob]:
        """Get a crawl job by ID for a specific tenant."""
        stmt = select(CrawlJob).where(
            CrawlJob.id == job_id,
            CrawlJob.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_job_status(
        self, job_id: str, status: CrawlJobStatus, **kwargs
    ) -> Optional[CrawlJob]:
        """Update job status and optionally other fields."""
        job = await self.get_job(job_id)
        if not job:
            return None

        job.status = status
        if "stats" in kwargs:
            job.stats = {**job.stats, **kwargs.pop("stats")}
        if "error_message" in kwargs:
            job.error_message = kwargs.pop("error_message")
        if "pages_crawled" in kwargs:
            job.pages_crawled = kwargs.pop("pages_crawled")
        if "chunks_created" in kwargs:
            job.chunks_created = kwargs.pop("chunks_created")

        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def list_jobs_by_tenant(
        self, tenant_id: str, limit: int = 10, offset: int = 0
    ) -> List[CrawlJob]:
        """List crawl jobs for a tenant, ordered by created_at descending."""
        stmt = select(CrawlJob).where(
            CrawlJob.tenant_id == tenant_id
        ).order_by(desc(CrawlJob.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_job_stats(
        self, job_id: str, stats: Dict[str, Any]
    ) -> Optional[CrawlJob]:
        """Update job statistics."""
        job = await self.get_job(job_id)
        if not job:
            return None

        current_stats = dict(job.stats) if job.stats else {}
        job.stats = {**current_stats, **stats}
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def delete_job(self, job_id: str) -> bool:
        """Delete a crawl job."""
        job = await self.get_job(job_id)
        if not job:
            return False

        await self.session.delete(job)
        await self.session.commit()
        return True


async def get_crawl_job(job_id: str) -> Optional[CrawlJob]:
    """Quick function to get a crawl job."""
    async with get_session() as session:
        repo = CrawlJobRepository(session)
        return await repo.get_job(job_id)


async def create_crawl_job(
    tenant_id: str,
    url: str,
    max_depth: int = 1,
) -> CrawlJob:
    """Quick function to create a crawl job."""
    async with get_session() as session:
        repo = CrawlJobRepository(session)
        return await repo.create_job(tenant_id, url, max_depth)
