"""FastAPI dependency functions for gateway service."""

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from shared.utils.errors import AuthError
from shared.utils.logging import get_logger

from app.models.schemas import TokenVerifyResponse
from app.utils.redis import get_redis_client, close_redis_client

logger = get_logger(__name__)

security = HTTPBearer(auto_error=False)


async def get_current_tenant(
    request: Request,
) -> dict:
    """Dependency to get current tenant from request state.

    Args:
        request: FastAPI request object

    Returns:
        Tenant dict from request.state.tenant

    Raises:
        HTTPException: If tenant is not available
    """
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )
    return tenant


async def get_tenant_id(
    request: Request,
) -> str:
    """Dependency to get tenant_id from request state.

    Args:
        request: FastAPI request object

    Returns:
        tenant_id string

    Raises:
        HTTPException: If tenant_id is not available
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )
    return tenant_id


async def get_redis() -> AsyncGenerator:
    """Dependency to get Redis client.

    Yields:
        Redis client instance
    """
    client = await get_redis_client()
    try:
        yield client
    finally:
        pass  # Client is a singleton, don't close


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenVerifyResponse:
    """Dependency to verify JWT token.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        TokenVerifyResponse with validity info
    """
    if not credentials:
        return TokenVerifyResponse(
            valid=False,
            error="Missing credentials",
        )

    try:
        from app.services.auth_service import (
            extract_tenant_id_from_token,
            create_auth_token,
        )

        tenant_id = extract_tenant_id_from_token(credentials.credentials)
        return TokenVerifyResponse(
            valid=True,
            tenant_id=tenant_id,
        )
    except AuthError as exc:
        return TokenVerifyResponse(
            valid=False,
            error=str(exc),
        )
