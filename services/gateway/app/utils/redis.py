"""Redis client singleton for gateway service."""

import os
from typing import Optional

import redis.asyncio as redis

from shared.utils.logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[redis.Redis] = None
_redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_redis_url() -> str:
    """Get Redis URL from environment variable."""
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def get_redis_client() -> redis.Redis:
    """Get Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        redis_url = get_redis_url()
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        logger.info("Redis client initialized", url=redis_url)
    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")


async def ensure_redis_connection() -> bool:
    """Check if Redis is connected and healthy."""
    try:
        client = await get_redis_client()
        await client.ping()
        return True
    except redis.ConnectionError:
        return False
