"""Celery task for full crawl pipeline."""

import asyncio
from datetime import datetime
from typing import Any, Dict

from celery import Celery
from structlog import get_logger

from app.services.crawler import Crawler
from app.services.html_cleaner import HTMLCleaner
from app.services.chunker import Chunker
from app.services.indexer import Indexer
from app.db.repository import CrawlJobRepository
from config import settings
from shared.db.base import get_session
from shared.models.crawl import CrawlJobStatus

logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "crawler_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BROKER_URL,
    include=["crawler_service.tasks.crawl_task"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # Warn at 4 minutes
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
async def crawl_task(
    self,
    job_id: str,
    tenant_id: str,
    url: str,
    max_depth: int = 1,
    exclude_patterns: list[str] | None = None,
) -> Dict[str, Any]:
    """Full crawl pipeline: crawl -> clean -> chunk -> index.

    Status transitions: pending -> running -> complete -> failed
    """
    logger.info(
        "crawl_task_started",
        job_id=job_id,
        tenant_id=tenant_id,
        url=url,
        max_depth=max_depth,
    )

    # Update status to running
    async with session_factory() as session:
        repo = CrawlJobRepository(session)
        await repo.update_job_status(
            job_id,
            CrawlJobStatus.RUNNING,
            stats={"max_depth": max_depth},
        )

    try:
        # Initialize services
        crawler = Crawler(
            max_depth=max_depth,
            exclude_patterns=exclude_patterns,
        )
        html_cleaner = HTMLCleaner()
        chunker = Chunker()
        async with Indexer() as indexer:
            # Run crawl
            result = await crawler.crawl(url)

            # Process pages
            chunks = []
            pages_crawled = 0
            pages_failed = 0

            for page in result["pages"]:
                # Clean HTML
                content = html_cleaner.clean(page["html"])
                if not content:
                    pages_failed += 1
                    continue

                # Chunk content
                page_chunks = chunker.chunk(content, page["url"])
                chunks.extend(page_chunks)
                pages_crawled += 1

            # Index chunks
            if chunks:
                index_result = await indexer.index_chunks(
                    tenant_id=tenant_id,
                    source_url=url,
                    chunks=chunks,
                )
            else:
                index_result = {"success": True, "chunks_indexed": 0}

            # Update job status to complete
            async with session_factory() as session:
                repo = CrawlJobRepository(session)
                await repo.update_job_status(
                    job_id,
                    CrawlJobStatus.COMPLETED,
                    stats={
                        "pages_crawled": pages_crawled,
                        "pages_failed": pages_failed,
                        "chunks_created": len(chunks),
                    },
                    pages_crawled=pages_crawled,
                    chunks_created=len(chunks),
                )

            logger.info(
                "crawl_task_completed",
                job_id=job_id,
                pages_crawled=pages_crawled,
                chunks_created=len(chunks),
                chunks_indexed=index_result.get("chunks_indexed", 0),
            )

            return {
                "success": True,
                "job_id": job_id,
                "pages_crawled": pages_crawled,
                "pages_failed": pages_failed,
                "chunks_created": len(chunks),
                "chunks_indexed": index_result.get("chunks_indexed", 0),
            }

    except Exception as exc:
        logger.error(
            "crawl_task_failed",
            job_id=job_id,
            error=str(exc),
            exc_info=True,
        )

        # Update job status to failed
        async with session_factory() as session:
            repo = CrawlJobRepository(session)
            await repo.update_job_status(
                job_id,
                CrawlJobStatus.FAILED,
                stats={"error": str(exc)},
                error_message=str(exc),
            )

        # Retry the task if not max retries
        if self.request.retries < self.max_retries:
            logger.warning(
                "crawl_task_retrying",
                job_id=job_id,
                retries=self.request.retries,
                max_retries=self.max_retries,
            )
            raise self.retry(exc=exc)

        raise


def get_celery_app() -> Celery:
    """Get the Celery app instance."""
    return celery_app
