"""Database repository for tenant and API key operations."""

from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.tenants import APIKey, Tenant
from shared.utils.errors import NotFoundError


class TenantRepository:
    """Repository for tenant database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, name: str, tenant_id: str, website_url: Optional[str] = None,
                     api_key_hash: str = "", default_llm_model: Optional[str] = None) -> Tenant:
        """Create a new tenant.

        Args:
            name: Tenant name
            tenant_id: Unique tenant identifier
            website_url: Optional website URL
            api_key_hash: Bcrypt-hashed API key
            default_llm_model: Optional default LLM model

        Returns:
            Created Tenant object
        """
        import uuid

        tenant = Tenant(
            id=str(uuid.uuid4()),
            name=name,
            tenant_id=tenant_id,
            website_url=website_url,
            api_key_hash=api_key_hash,
            default_llm_model=default_llm_model,
            is_active=True,
        )
        self.session.add(tenant)
        await self.session.commit()
        await self.session.refresh(tenant)
        return tenant

    async def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            Tenant object or None if not found
        """
        result = await self.session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_active(self, tenant_id: str) -> Optional[Tenant]:
        """Get active tenant by ID.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            Active Tenant object or None if not found/inactive
        """
        result = await self.session.execute(
            select(Tenant).where(
                Tenant.tenant_id == tenant_id,
                Tenant.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def list(self, limit: int = 100, offset: int = 0) -> List[Tenant]:
        """List tenants with pagination.

        Args:
            limit: Maximum number of tenants to return
            offset: Number of tenants to skip

        Returns:
            List of Tenant objects
        """
        result = await self.session.execute(
            select(Tenant)
            .order_by(Tenant.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """Get total count of all tenants.

        Returns:
            Total count of tenants
        """
        from sqlalchemy import func

        result = await self.session.execute(select(func.count(Tenant.id)))
        return result.scalar_one()

    async def soft_delete(self, tenant_id: str) -> bool:
        """Soft delete a tenant.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            True if tenant was found and deleted, False otherwise
        """
        result = await self.session.execute(
            update(Tenant)
            .where(Tenant.tenant_id == tenant_id)
            .values(is_active=False)
        )
        await self.session.commit()
        return result.rowcount > 0


class APIKeyRepository:
    """Repository for API key database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_id: str, key_hash: str, name: str,
                     expires_at: Optional[str] = None) -> APIKey:
        """Create a new API key.

        Args:
            tenant_id: Tenant identifier
            key_hash: Bcrypt-hashed API key
            name: Key name for identification
            expires_at: Optional expiration datetime

        Returns:
            Created APIKey object
        """
        import uuid

        api_key = APIKey(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            key_hash=key_hash,
            name=name,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            is_active=True,
        )
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        return api_key

    async def get_by_id(self, tenant_id: str, key_id: str) -> Optional[APIKey]:
        """Get API key by ID.

        Args:
            tenant_id: Tenant identifier
            key_id: API key identifier

        Returns:
            APIKey object or None if not found
        """
        result = await self.session.execute(
            select(APIKey).where(
                APIKey.tenant_id == tenant_id,
                APIKey.id == key_id
            )
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: str) -> List[APIKey]:
        """List all API keys for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of APIKey objects
        """
        result = await self.session.execute(
            select(APIKey)
            .where(APIKey.tenant_id == tenant_id)
            .order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def rotate(self, tenant_id: str, key_id: str, new_key_hash: str) -> APIKey:
        """Rotate an API key.

        Args:
            tenant_id: Tenant identifier
            key_id: API key identifier
            new_key_hash: New bcrypt-hashed API key

        Returns:
            Updated APIKey object
        """
        result = await self.session.execute(
            update(APIKey)
            .where(
                APIKey.tenant_id == tenant_id,
                APIKey.id == key_id
            )
            .values(
                key_hash=new_key_hash,
                is_active=True,
            )
        )
        await self.session.commit()

        # Refresh the key to get updated values
        updated_key = await self.get_by_id(tenant_id, key_id)
        if not updated_key:
            raise NotFoundError("APIKey", key_id)
        return updated_key

    async def revoke(self, tenant_id: str, key_id: str) -> bool:
        """Revoke an API key.

        Args:
            tenant_id: Tenant identifier
            key_id: API key identifier

        Returns:
            True if key was found and revoked, False otherwise
        """
        result = await self.session.execute(
            update(APIKey)
            .where(
                APIKey.tenant_id == tenant_id,
                APIKey.id == key_id
            )
            .values(is_active=False)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def delete(self, tenant_id: str, key_id: str) -> bool:
        """Permanently delete an API key.

        Args:
            tenant_id: Tenant identifier
            key_id: API key identifier

        Returns:
            True if key was found and deleted, False otherwise
        """
        result = await self.session.execute(
            delete(APIKey).where(
                APIKey.tenant_id == tenant_id,
                APIKey.id == key_id
            )
        )
        await self.session.commit()
        return result.rowcount > 0
