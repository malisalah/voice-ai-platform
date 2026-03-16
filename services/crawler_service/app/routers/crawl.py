"""Crawl job endpoints."""

from datetime import datetime
from http import HTTPStatus

from fastapi import APIRouter, BackgroundTasks, HTTPException

from structlog import get_logger

from app.models.schemas import (
    CrawlRequest,
    CrawlResponse,
    CrawlJobResponse,
    ChunkListResponse,
)
from app.services.crawler import Crawler
from app.services.html_cleaner import HTMLCleaner
from app.services.chunker import Chunker
from config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/crawl", tags=["crawl"])


# In-memory job storage (replace with database in production)
_crawl_jobs: dict = {}


@router.post("", status_code=HTTPStatus.ACCEPTED, response_model=CrawlResponse)
async def trigger_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger a new crawl job."""
    from uuid import uuid4

    job_id = str(uuid4())

    # Store job state
    _crawl_jobs[job_id] = {
        "job_id": job_id,
        "url": request.url,
        "status": "pending",
        "stats": {},
        "created_at": datetime.now().isoformat(),
    }

    # Start crawl in background
    background_tasks.add_task(_run_crawl, job_id, request)

    return CrawlResponse(
        job_id=job_id,
        status="pending",
        message=f"Crawl job {job_id} started for {request.url}",
    )


@router.get("/{job_id}", response_model=CrawlJobResponse)
async def get_crawl_status(job_id: str):
    """Get the status of a crawl job."""
    if job_id not in _crawl_jobs:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Crawl job {job_id} not found",
        )

    job = _crawl_jobs[job_id]

    return CrawlJobResponse(
        id=job_id,
        tenant_id=job.get("tenant_id", "unknown"),
        url=job["url"],
        status=job["status"],
        stats=job.get("stats", {}),
        error_message=job.get("error_message"),
        pages_crawled=job.get("pages_crawled", 0),
        chunks_created=job.get("chunks_created", 0),
        created_at=job["created_at"],
        updated_at=job.get("updated_at", job["created_at"]),
    )


@router.get("/{job_id}/chunks", response_model=ChunkListResponse)
async def get_crawl_chunks(job_id: str):
    """Get chunks from a completed crawl job."""
    if job_id not in _crawl_jobs:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Crawl job {job_id} not found",
        )

    job = _crawl_jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Crawl job {job_id} is not completed yet",
        )

    chunks = job.get("chunks", [])
    return ChunkListResponse(
        chunks=chunks,
        total_chunks=len(chunks),
        job_id=job_id,
    )


async def _run_crawl(job_id: str, request: CrawlRequest):
    """Run the crawl process in background."""
    from datetime import datetime

    try:
        # Initialize services with config values
        crawler = Crawler(
            max_depth=request.max_depth or settings.CRAWLER_MAX_DEPTH,
            max_pages=settings.CRAWLER_MAX_PAGES,
            delay=settings.CRAWLER_DELAY_SECONDS,
            exclude_patterns=set(request.exclude_patterns or []),
            user_agent=settings.CRAWLER_USER_AGENT,
        )

        html_cleaner = HTMLCleaner()
        chunker = Chunker(
            max_words=settings.POCKETFLOW_CHUNK_SIZE,
            overlap_words=settings.POCKETFLOW_CHUNK_OVERLAP,
        )

        # Run crawl
        result = await crawler.crawl(request.url)

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

        # Update job state
        _crawl_jobs[job_id].update({
            "status": "completed",
            "updated_at": datetime.now().isoformat(),
            "stats": {
                "pages_crawled": pages_crawled,
                "pages_failed": pages_failed,
                "chunks_created": len(chunks),
            },
            "chunks": chunks,
            "pages_crawled": pages_crawled,
            "chunks_created": len(chunks),
        })

    except Exception as e:
        logger.error("crawl_error", job_id=job_id, error=str(e))

        _crawl_jobs[job_id].update({
            "status": "failed",
            "updated_at": datetime.now().isoformat(),
            "error_message": str(e),
        })
