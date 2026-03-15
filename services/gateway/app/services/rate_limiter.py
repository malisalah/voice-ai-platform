"""Rate limiter service using Redis sliding window algorithm."""

import time
from typing import Tuple

from shared.utils.errors import RateLimitExceededError
from shared.utils.logging import get_logger

from app.utils.redis import get_redis_client

logger = get_logger(__name__)

DEFAULT_RATE_LIMIT_PER_MINUTE = 60
REDIS_KEY_PREFIX = "rate_limit:"


async def check_rate_limit(
    tenant_id: str,
    endpoint: str,
    rate_limit_per_minute: int = None,
) -> Tuple[bool, int, int]:
    """Check if request is within rate limit using sliding window.

    Args:
        tenant_id: The tenant ID
        endpoint: The API endpoint path
        rate_limit_per_minute: Max requests per minute (uses env if None)

    Returns:
        Tuple of (allowed, remaining_requests, reset_seconds)

    Raises:
        RateLimitExceededError: If rate limit exceeded
    """
    if rate_limit_per_minute is None:
        rate_limit_per_minute = DEFAULT_RATE_LIMIT_PER_MINUTE

    client = await get_redis_client()

    key = f"{REDIS_KEY_PREFIX}{tenant_id}:{endpoint}"
    now = time.time()
    window_start = now - 60

    # Use pipeline for atomic operation
    pipe = client.pipeline()
    pipe.zremrangebyscore(key, "-inf", window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, 65)  # 5 seconds buffer
    results = await pipe.execute()

    current_count = results[2]

    if current_count > rate_limit_per_minute:
        logger.warning(
            "Rate limit exceeded",
            tenant_id=tenant_id,
            endpoint=endpoint,
            count=current_count,
            limit=rate_limit_per_minute,
        )
        raise RateLimitExceededError(
            f"Rate limit exceeded. Try again in 60 seconds."
        )

    remaining = max(0, rate_limit_per_minute - current_count)
    reset_at = now + 60

    return True, remaining, int(reset_at - now)


async def get_rate_limit_status(
    tenant_id: str,
    endpoint: str,
    rate_limit_per_minute: int = None,
) -> Tuple[int, int, float]:
    """Get current rate limit status without consuming quota.

    Args:
        tenant_id: The tenant ID
        endpoint: The API endpoint path
        rate_limit_per_minute: Max requests per minute

    Returns:
        Tuple of (current_count, remaining, reset_timestamp)
    """
    if rate_limit_per_minute is None:
        rate_limit_per_minute = DEFAULT_RATE_LIMIT_PER_MINUTE

    client = await get_redis_client()

    key = f"{REDIS_KEY_PREFIX}{tenant_id}:{endpoint}"
    now = time.time()
    window_start = now - 60

    # Clean old entries and get count
    pipe = client.pipeline()
    pipe.zremrangebyscore(key, "-inf", window_start)
    pipe.zcard(key)
    results = await pipe.execute()

    current_count = results[1]
    remaining = max(0, rate_limit_per_minute - current_count)
    reset_at = now + 60

    return current_count, remaining, reset_at


async def reset_rate_limit(tenant_id: str, endpoint: str) -> None:
    """Reset rate limit for a tenant+endpoint combination.

    Args:
        tenant_id: The tenant ID
        endpoint: The API endpoint path
    """
    client = await get_redis_client()
    key = f"{REDIS_KEY_PREFIX}{tenant_id}:{endpoint}"
    await client.delete(key)
    logger.info("Rate limit reset", tenant_id=tenant_id, endpoint=endpoint)
