"""Business logic for API key operations."""

import bcrypt
from typing import Optional

from shared.utils.errors import NotFoundError

from app.db.repository import APIKeyRepository
from app.models.schemas import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyResponse,
)
from app.utils.crypto import generate_secure_key
from shared.models.tenants import APIKey


class APIKeyService:
    """Service for API key management operations."""

    def __init__(self, session):
        self.session = session
        self.api_key_repo = APIKeyRepository(session)

    async def create_api_key(
        self, tenant_id: str, request: APIKeyCreateRequest
    ) -> APIKeyCreateResponse:
        """Create a new API key for a tenant.

        Args:
            tenant_id: Tenant identifier
            request: API key creation request

        Returns:
            APIKeyCreateResponse with plain key (returned ONLY once)
        """
        # Generate secure key
        plain_key = generate_secure_key()

        # Hash with bcrypt
        key_hash = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()

        # Calculate expiration
        expires_at = None
        if request.expires_days:
            from datetime import datetime, timedelta, timezone
            expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_days)

        # Create API key in database
        api_key = await self.api_key_repo.create(
            tenant_id=tenant_id,
            key_hash=key_hash,
            name=request.name,
            expires_at=expires_at,
        )

        # Return response with plain key (must be shown ONLY once)
        return APIKeyCreateResponse(
            id=str(api_key.id),
            tenant_id=api_key.tenant_id,
            name=api_key.name,
            key=plain_key,  # Plain key - returned ONLY at creation!
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            is_active=api_key.is_active,
        )

    async def get_api_key(self, tenant_id: str, key_id: str) -> APIKeyResponse:
        """Get API key by ID.

        Args:
            tenant_id: Tenant identifier
            key_id: API key identifier

        Returns:
            APIKeyResponse with key data

        Raises:
            NotFoundError: If key not found
        """
        api_key = await self.api_key_repo.get_by_id(tenant_id, key_id)
        if not api_key:
            raise NotFoundError("APIKey", key_id)

        return APIKeyResponse(
            id=str(api_key.id),
            tenant_id=api_key.tenant_id,
            name=api_key.name,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            is_active=api_key.is_active,
        )

    async def list_api_keys(self, tenant_id: str) -> list[APIKeyResponse]:
        """List all API keys for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of APIKeyResponse objects
        """
        api_keys = await self.api_key_repo.list_by_tenant(tenant_id)

        return [
            APIKeyResponse(
                id=str(key.id),
                tenant_id=key.tenant_id,
                name=key.name,
                created_at=key.created_at,
                expires_at=key.expires_at,
                is_active=key.is_active,
            )
            for key in api_keys
        ]

    async def rotate_api_key(
        self, tenant_id: str, key_id: str
    ) -> APIKeyCreateResponse:
        """Rotate an API key.

        Args:
            tenant_id: Tenant identifier
            key_id: API key identifier

        Returns:
            APIKeyCreateResponse with new plain key

        Raises:
            NotFoundError: If key not found
        """
        # Verify key exists before rotation
        api_key = await self.api_key_repo.get_by_id(tenant_id, key_id)
        if not api_key:
            raise NotFoundError("APIKey", key_id)

        # Generate new secure key
        new_plain_key = generate_secure_key()

        # Hash with bcrypt
        new_key_hash = bcrypt.hashpw(
            new_plain_key.encode(), bcrypt.gensalt()
        ).decode()

        # Rotate in database
        rotated_key = await self.api_key_repo.rotate(
            tenant_id=tenant_id,
            key_id=key_id,
            new_key_hash=new_key_hash,
        )

        # Return response with new plain key (must be shown ONLY once)
        return APIKeyCreateResponse(
            id=str(rotated_key.id),
            tenant_id=rotated_key.tenant_id,
            name=rotated_key.name,
            key=new_plain_key,  # New plain key - returned ONLY at rotation!
            created_at=rotated_key.created_at,
            expires_at=rotated_key.expires_at,
            is_active=rotated_key.is_active,
        )

    async def revoke_api_key(self, tenant_id: str, key_id: str) -> bool:
        """Revoke an API key.

        Args:
            tenant_id: Tenant identifier
            key_id: API key identifier

        Returns:
            True if key was found and revoked

        Raises:
            NotFoundError: If key not found
        """
        api_key = await self.api_key_repo.get_by_id(tenant_id, key_id)
        if not api_key:
            raise NotFoundError("APIKey", key_id)

        return await self.api_key_repo.revoke(tenant_id=tenant_id, key_id=key_id)

    async def delete_api_key(self, tenant_id: str, key_id: str) -> bool:
        """Permanently delete an API key.

        Args:
            tenant_id: Tenant identifier
            key_id: API key identifier

        Returns:
            True if key was found and deleted
        """
        return await self.api_key_repo.delete(
            tenant_id=tenant_id, key_id=key_id
        )


async def get_api_key_service(session) -> APIKeyService:
    """Get an API key service instance."""
    return APIKeyService(session)
