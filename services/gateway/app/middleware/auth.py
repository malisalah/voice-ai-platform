"""Authentication middleware - validates JWT on incoming requests."""

from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from shared.utils.errors import AuthError
from shared.utils.logging import get_logger

logger = get_logger(__name__)

# Routes that skip auth middleware
SKIP_AUTH_PATHS = {"/health", "/auth/token", "/auth/verify"}
logger.info("Auth middleware initialized", skip_paths=list(SKIP_AUTH_PATHS))


class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that validates JWT tokens on incoming requests.

    Skips authentication for:
    - /health
    - /auth/token
    - /auth/verify

    Extracts tenant_id from JWT payload and attaches to request.state.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        path = request.url.path
        logger.info("Auth middleware check", path=path, skip_paths=list(SKIP_AUTH_PATHS))

        # Skip auth for public routes
        if any(path.startswith(skip_path) for skip_path in SKIP_AUTH_PATHS):
            logger.info("Auth skipped", path=path)
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("Missing Authorization header", path=path)
            return JSONResponse(
                status_code=401,
                content={"error": "Missing Authorization header"},
            )

        # Handle Bearer token format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning("Invalid Authorization header format", path=path)
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid Authorization header format"},
            )

        token = parts[1]

        # Validate token and extract tenant_id
        try:
            from app.services.auth_service import extract_tenant_id_from_token

            tenant_id = extract_tenant_id_from_token(token)
            request.state.tenant_id = tenant_id
            request.state.token = token

            logger.debug(
                "Token validated successfully",
                path=path,
                tenant_id=tenant_id,
            )

        except AuthError as exc:
            logger.warning("Token validation failed", path=path, error=str(exc))
            return JSONResponse(
                status_code=401,
                content={"error": str(exc)},
            )

        return await call_next(request)
