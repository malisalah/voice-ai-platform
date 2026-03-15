"""Routers for tenant management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from shared.db.base import get_session
from shared.models.tenants import Tenant
from shared.utils.auth import decode_token
from shared.utils.errors import (
    APIError,
    AuthError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
)

from app.models.schemas import (
    TenantCreateRequest,
    TenantResponse,
    TenantUpdateRequest,
    MessageResponse,
)
from app.services.tenant_service import TenantService, get_tenant_service

router = APIRouter(prefix="/tenants", tags=["tenants"])


async def get_current_tenant_id(
    authorization: str = Query(None, alias="Authorization"),
    session: AsyncSession = Depends(get_session),
) -> str:
    """Extract tenant_id from JWT token or API key.

    Args:
        authorization: Bearer token or API key
        session: Database session

    Returns:
        Tenant ID string

    Raises:
        AuthError: If no valid auth provided
    """
    if not authorization:
        raise AuthError("Authorization header required")

    # Try JWT token first
    if authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            claims = decode_token(token)
            return claims["sub"]
        except AuthError:
            raise AuthError("Invalid token")

    # Try API key
    from sqlalchemy import select
    from shared.models.tenants import APIKey

    result = await session.execute(
        select(Tenant).join(APIKey).where(APIKey.key_hash == authorization)
    )
    tenant = result.scalar_one_or_none()
    if tenant:
        return tenant.tenant_id

    raise AuthError("Invalid authorization")


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    request: TenantCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new tenant with initial API key.

    Args:
        request: Tenant creation request
        session: Database session

    Returns:
        Created tenant data

    Raises:
        HTTPException: On validation or database errors
    """
    try:
        service = TenantService(session)
        tenant = await service.create_tenant(request)
        return tenant
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get tenant by ID.

    Args:
        tenant_id: Tenant identifier
        session: Database session

    Returns:
        Tenant data

    Raises:
        HTTPException: If tenant not found
    """
    try:
        service = TenantService(session)
        tenant = await service.get_tenant(tenant_id)
        return tenant
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)


@router.get("", response_model=dict)
async def list_tenants(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List tenants with pagination.

    Args:
        limit: Maximum number of tenants to return
        offset: Number of tenants to skip
        session: Database session

    Returns:
        Dict with items, total, limit, offset
    """
    try:
        service = TenantService(session)
        result = await service.list_tenants(limit=limit, offset=offset)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{tenant_id}", response_model=MessageResponse)
async def delete_tenant(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Soft delete a tenant.

    Args:
        tenant_id: Tenant identifier
        session: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If tenant not found
    """
    try:
        service = TenantService(session)
        await service.delete_tenant(tenant_id)
        return MessageResponse(message="Tenant deleted successfully")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    request: TenantUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update a tenant.

    Args:
        tenant_id: Tenant identifier
        request: Update request
        session: Database session

    Returns:
        Updated tenant data

    Raises:
        HTTPException: If tenant not found
    """
    try:
        service = TenantService(session)
        tenant = await service.update_tenant(tenant_id, request)
        return tenant
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)
