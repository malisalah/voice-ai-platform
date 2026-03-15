"""Rate limiting middleware using Redis sliding window."""

import os
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from shared.utils.errors import RateLimitExceededError
from shared.utils.logging import get_logger

from app.services.rate_limiter import check_rate_limit

logger = get_logger(__name__)

# Environment variable for rate limit
DEFAULT_RATE_LIMIT_PER_MINUTE = int(
    os.getenv("RATE_LIMIT_PER_MINUTE", "60")
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that implements rate limiting per tenant.

    Rate limit key: f"{tenant_id}:{endpoint}"
    Returns 429 with Retry-After header when limit exceeded.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Skip rate limiting for public routes
        path = request.url.path
        if path.startswith(("/health", "/auth")):
            return await call_next(request)

        # Get tenant_id from request state
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            # No tenant - could be pre-auth or public endpoint
            return await call_next(request)

        # Get rate limit from env or use default
        rate_limit = int(
            os.getenv("RATE_LIMIT_PER_MINUTE", DEFAULT_RATE_LIMIT_PER_MINUTE)
        )

        # Extract endpoint (base path without query params)
        endpoint = path.split("?")[0]

        try:
            allowed, remaining, reset_seconds = await check_rate_limit(
                tenant_id=tenant_id,
                endpoint=endpoint,
                rate_limit_per_minute=rate_limit,
            )

            # Add rate limit headers to response
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_seconds)

            logger.debug(
                "Rate limit check passed",
                tenant_id=tenant_id,
                endpoint=endpoint,
                remaining=remaining,
            )

            return response

        except RateLimitExceededError as exc:
            logger.warning(
                "Rate limit exceeded",
                tenant_id=tenant_id,
                endpoint=endpoint,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": str(exc),
                    "tenant_id": tenant_id,
                    "endpoint": endpoint,
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(rate_limit),
                    "X-RateLimit-Remaining": "0",
                },
            )
