"""Routers for API key management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.base import get_session
from shared.utils.auth import decode_token
from shared.utils.errors import AuthError, NotFoundError

from app.models.schemas import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyResponse,
    MessageResponse,
)
from app.services.api_key_service import APIKeyService, get_api_key_service

router = APIRouter(prefix="/tenants/{tenant_id}/api-keys", tags=["api_keys"])


async def get_api_key_service_dependency(
    session: AsyncSession = Depends(get_session),
) -> APIKeyService:
    """Get an API key service instance."""
    return APIKeyService(session)


@router.post("", response_model=APIKeyCreateResponse, status_code=201)
async def create_api_key(
    tenant_id: str,
    request: APIKeyCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new API key for a tenant.

    Args:
        tenant_id: Tenant identifier
        request: API key creation request
        session: Database session

    Returns:
        API key data with plain key (returned ONLY once)

    Raises:
        HTTPException: If tenant not found or other errors
    """
    try:
        service = APIKeyService(session)
        api_key = await service.create_api_key(tenant_id, request)
        return api_key
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("", response_model=list[APIKeyResponse])
async def list_api_keys(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
):
    """List all API keys for a tenant.

    Args:
        tenant_id: Tenant identifier
        session: Database session

    Returns:
        List of API key data

    Raises:
        HTTPException: If tenant not found
    """
    try:
        service = APIKeyService(session)
        api_keys = await service.list_api_keys(tenant_id)
        return api_keys
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)


@router.post("/{key_id}/rotate", response_model=APIKeyCreateResponse)
async def rotate_api_key(
    tenant_id: str,
    key_id: str = Path(..., description="API key identifier"),
    session: AsyncSession = Depends(get_session),
):
    """Rotate an API key.

    Args:
        tenant_id: Tenant identifier
        key_id: API key identifier
        session: Database session

    Returns:
        New API key data with plain key (returned ONLY once)

    Raises:
        HTTPException: If key not found
    """
    try:
        service = APIKeyService(session)
        api_key = await service.rotate_api_key(tenant_id, key_id)
        return api_key
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)


@router.patch("/{key_id}/revoke", response_model=MessageResponse)
async def revoke_api_key(
    tenant_id: str,
    key_id: str = Path(..., description="API key identifier"),
    session: AsyncSession = Depends(get_session),
):
    """Revoke an API key.

    Args:
        tenant_id: Tenant identifier
        key_id: API key identifier
        session: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If key not found
    """
    try:
        service = APIKeyService(session)
        await service.revoke_api_key(tenant_id, key_id)
        return MessageResponse(message="API key revoked successfully")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)


@router.delete("/{key_id}", response_model=MessageResponse)
async def delete_api_key(
    tenant_id: str,
    key_id: str = Path(..., description="API key identifier"),
    session: AsyncSession = Depends(get_session),
):
    """Permanently delete an API key.

    Args:
        tenant_id: Tenant identifier
        key_id: API key identifier
        session: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If key not found
    """
    try:
        service = APIKeyService(session)
        await service.delete_api_key(tenant_id, key_id)
        return MessageResponse(message="API key deleted successfully")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)
