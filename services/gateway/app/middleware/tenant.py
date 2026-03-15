"""Tenant middleware - validates tenant exists and is active."""

from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from shared.utils.errors import NotFoundError
from shared.utils.logging import get_logger

from app.services.proxy import call_tenant_service

logger = get_logger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that validates tenant exists and is active.

    Reads tenant_id from request.state (set by auth middleware).
    Rejects with 403 if tenant is inactive or not found.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Skip tenant validation for certain paths (including health)
        path = request.url.path
        if path.startswith(("/health", "/auth", "/docs", "/openapi.json")):
            return await call_next(request)

        # Check if tenant_id was set by auth middleware
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            # This shouldn't happen if auth middleware is properly configured
            return JSONResponse(
                status_code=401,
                content={"error": "Authentication required"},
            )

        # Verify tenant exists and is active
        try:
            result = await call_tenant_service(
                method="GET",
                path=f"/tenants/{tenant_id}",
            )

            if not result.get("is_active", True):
                logger.warning(
                    "Inactive tenant attempted access",
                    tenant_id=tenant_id,
                    path=path,
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Tenant account is inactive",
                        "tenant_id": tenant_id,
                    },
                )

            # Attach tenant data to request state
            request.state.tenant = result

            logger.debug(
                "Tenant validated successfully",
                tenant_id=tenant_id,
                tenant_name=result.get("name"),
            )

        except NotFoundError:
            logger.warning(
                "Tenant not found",
                tenant_id=tenant_id,
                path=path,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Tenant not found or unauthorized",
                    "tenant_id": tenant_id,
                },
            )

        return await call_next(request)
