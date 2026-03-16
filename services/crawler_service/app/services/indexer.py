"""Indexer service for sending chunks to knowledge-service."""

import asyncio
from typing import Any, Dict, List
from uuid import uuid4

import httpx
from structlog import get_logger

from config import settings

logger = get_logger(__name__)


class Indexer:
    """Send chunked content to knowledge-service with retries."""

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 30,
        client: httpx.AsyncClient | None = None,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self._client = client

    async def __aenter__(self) -> "Indexer":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def index_chunks(
        self,
        tenant_id: str,
        source_url: str,
        chunks: List[Dict[str, Any]],
        client: httpx.AsyncClient | None = None,
    ) -> Dict[str, Any]:
        """Send chunks to knowledge-service for indexing."""
        use_client = client or self._client
        if not use_client:
            raise RuntimeError("Indexer not initialized. Pass a client or use async context manager.")

        url = f"{settings.KNOWLEDGE_SERVICE_URL}/ingest"
        payload = {
            "tenant_id": tenant_id,
            "source_url": source_url,
            "chunks": chunks,
            "job_id": str(uuid4()),
        }

        for attempt in range(self.max_retries):
            try:
                response = await use_client.post(
                    url,
                    json=payload,
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        "chunks_indexed",
                        tenant_id=tenant_id,
                        chunks_sent=len(chunks),
                        knowledge_job_id=result.get("job_id"),
                    )
                    return result

                elif response.status_code >= 500:
                    # Server error - retry
                    logger.warning(
                        "indexer_server_error",
                        attempt=attempt + 1,
                        status_code=response.status_code,
                        url=url,
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                else:
                    # Client error - don't retry
                    logger.error(
                        "indexer_client_error",
                        status_code=response.status_code,
                        response=response.text,
                    )
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "chunks_sent": len(chunks),
                    }

            except httpx.RequestError as e:
                logger.error(
                    "indexer_request_failed",
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise

        raise RuntimeError(f"Failed to index chunks after {self.max_retries} retries")

    async def index_single_chunk(
        self,
        tenant_id: str,
        source_url: str,
        chunk: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Index a single chunk."""
        return await self.index_chunks(tenant_id, source_url, [chunk])

    def format_chunk(
        self,
        content: str,
        page_url: str,
        chunk_index: int,
        word_count: int = 0,
        sentence_count: int = 0,
        char_count: int = 0,
    ) -> Dict[str, Any]:
        """Format a chunk for indexing."""
        return {
            "content": content,
            "page_url": page_url,
            "chunk_index": chunk_index,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "char_count": char_count,
            "created_at": asyncio.get_event_loop().time(),
        }


async def bulk_index(
    tenant_id: str,
    source_url: str,
    chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Quick function to index chunks using indexer context manager."""
    async with Indexer() as indexer:
        return await indexer.index_chunks(tenant_id, source_url, chunks)
