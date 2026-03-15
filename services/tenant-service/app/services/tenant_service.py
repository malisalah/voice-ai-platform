"""Business logic for tenant operations."""

import uuid
from typing import Optional

from shared.db.base import get_session
from shared.models.tenants import TenantCreate, TenantUpdate
from shared.utils.errors import ConflictError, NotFoundError

from app.db.repository import APIKeyRepository, TenantRepository
from app.models.schemas import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    TenantCreateRequest,
    TenantResponse,
    TenantUpdateRequest,
)


class TenantService:
    """Service for tenant management operations."""

    def __init__(self, session):
        self.session = session
        self.tenant_repo = TenantRepository(session)
        self.api_key_repo = APIKeyRepository(session)

    async def create_tenant(
        self, request: TenantCreateRequest, tenant_id: Optional[str] = None
    ) -> TenantResponse:
        """Create a new tenant with initial API key.

        Args:
            request: Tenant creation request
            tenant_id: Optional tenant ID (auto-generated if not provided)

        Returns:
            TenantResponse with created tenant data and API key
        """
        # Check for duplicate tenant name
        from sqlalchemy import select
        from shared.models.tenants import Tenant

        result = await self.session.execute(
            select(Tenant).where(Tenant.name == request.name)
        )
        existing = result.scalar_one_or_none()
        if existing and existing.is_active:
            raise ConflictError(f"Tenant with name '{request.name}' already exists")

        # Generate IDs
        tid = tenant_id or str(uuid.uuid4())

        from app.utils.crypto import generate_secure_key

        plain_key = generate_secure_key()

        import bcrypt

        key_hash = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()

        # Create tenant
        tenant = await self.tenant_repo.create(
            name=request.name,
            tenant_id=tid,
            website_url=request.website_url,
            api_key_hash=key_hash,
            default_llm_model=request.default_llm_model,
        )

        # Create initial API key
        api_key = await self.api_key_repo.create(
            tenant_id=tid,
            key_hash=key_hash,  # Same as tenant's API key for backward compatibility
            name=f"Default Key - {tenant.name}",
        )

        # Return response with plain key (returned ONLY once)
        return TenantResponse(
            id=str(tenant.id),
            tenant_id=tenant.tenant_id,
            name=tenant.name,
            website_url=tenant.website_url,
            is_active=tenant.is_active,
            default_llm_model=tenant.default_llm_model,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )

    async def get_tenant(self, tenant_id: str) -> TenantResponse:
        """Get tenant by ID.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            TenantResponse with tenant data

        Raises:
            NotFoundError: If tenant not found
        """
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)

        return TenantResponse(
            id=str(tenant.id),
            tenant_id=tenant.tenant_id,
            name=tenant.name,
            website_url=tenant.website_url,
            is_active=tenant.is_active,
            default_llm_model=tenant.default_llm_model,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )

    async def list_tenants(self, limit: int = 100, offset: int = 0) -> dict:
        """List tenants with pagination.

        Args:
            limit: Maximum number of tenants to return
            offset: Number of tenants to skip

        Returns:
            Dict with items, total, limit, offset
        """
        tenants = await self.tenant_repo.list(limit=limit, offset=offset)
        total = await self.tenant_repo.count()

        return {
            "items": [
                TenantResponse(
                    id=str(t.id),
                    tenant_id=t.tenant_id,
                    name=t.name,
                    website_url=t.website_url,
                    is_active=t.is_active,
                    default_llm_model=t.default_llm_model,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                for t in tenants
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def delete_tenant(self, tenant_id: str) -> bool:
        """Soft delete a tenant.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            True if tenant was found and deleted

        Raises:
            NotFoundError: If tenant not found
        """
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)

        return await self.tenant_repo.soft_delete(tenant_id)

    async def update_tenant(
        self, tenant_id: str, request: TenantUpdateRequest
    ) -> TenantResponse:
        """Update a tenant.

        Args:
            tenant_id: Unique tenant identifier
            request: Update request

        Returns:
            Updated TenantResponse

        Raises:
            NotFoundError: If tenant not found
        """
        from sqlalchemy import select, update
        from shared.models.tenants import Tenant

        # Check tenant exists
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)

        # Update fields
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.website_url is not None:
            update_data["website_url"] = request.website_url
        if request.is_active is not None:
            update_data["is_active"] = request.is_active
        if request.default_llm_model is not None:
            update_data["default_llm_model"] = request.default_llm_model

        if update_data:
            await self.session.execute(
                update(Tenant)
                .where(Tenant.tenant_id == tenant_id)
                .values(**update_data)
            )
            await self.session.commit()

        # Refresh and return
        updated = await self.tenant_repo.get_by_id(tenant_id)
        return TenantResponse(
            id=str(updated.id),
            tenant_id=updated.tenant_id,
            name=updated.name,
            website_url=updated.website_url,
            is_active=updated.is_active,
            default_llm_model=updated.default_llm_model,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )


async def get_tenant_service() -> TenantService:
    """Get a tenant service instance.

    Usage:
        service = await get_tenant_service()
    """
    session = get_session()
    return TenantService(session)
