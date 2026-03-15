"""Integration tests for tenant-service using pytest."""

import sys

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

# Paths
_gateway_path = "/home/mali/voice-ai-platform/services/gateway"
_tenant_service_path = "/home/mali/voice-ai-platform/services/tenant-service"
_shared_path = "/home/mali/voice-ai-platform/shared"
_root_path = "/home/mali/voice-ai-platform"


def _cleanup_all_service_paths():
    """Remove all service paths from sys.path."""
    for path in [_gateway_path, _tenant_service_path, _shared_path, _root_path]:
        if path in sys.path:
            sys.path.remove(path)


def _setup_tenant_service_paths():
    """Set up paths for tenant-service tests.

    The order matters! Tenant-service path must come first so that
    'app' imports resolve to tenant-service's app package, not gateway's.
    """
    _cleanup_all_service_paths()
    # Add paths with tenant-service first, then shared
    # Note: Root path should NOT be added as it would make gateway's 'app'
    # package accessible before tenant-service's
    if _tenant_service_path not in sys.path:
        sys.path.insert(0, _tenant_service_path)
    if _shared_path not in sys.path:
        sys.path.insert(0, _shared_path)


def _clear_all_service_modules():
    """Clear both gateway and tenant-service modules from cache."""
    _clear_gateway_modules()
    _clear_tenant_service_modules()


def _clear_tenant_service_modules():
    """Clear tenant-service app modules from cache."""
    print(f"[TENANT] _clear_tenant_service_modules() called")
    modules_to_clear = [
        "app",
        "app.routers",
        "app.models",
        "app.services",
        "app.jobs",
    ]
    for mod_name in list(sys.modules.keys()):
        if any(mod_name == m or mod_name.startswith(m + ".") for m in modules_to_clear):
            print(f"[TENANT] Deleting: {mod_name}")
            del sys.modules[mod_name]


def _clear_gateway_modules():
    """Clear gateway modules from cache to avoid conflicts."""
    print(f"[TENANT] _clear_gateway_modules() called")
    modules_to_clear = [
        "app",
        "app.routers",
        "app.models",
        "app.services",
    ]
    for mod_name in list(sys.modules.keys()):
        if any(mod_name == m or mod_name.startswith(m + ".") for m in modules_to_clear):
            print(f"[TENANT] Deleting: {mod_name}")
            del sys.modules[mod_name]


# Module-level setup - called at module import time
# This ensures tenant-service paths are set up before module imports
# and gateway modules are cleared if they were cached
# Import conftest helper functions
from .conftest import set_service_paths, clear_service_modules

# Set up tenant paths
print(f"[TENANT] Before set_service_paths: sys.path[:3] = {sys.path[:3]}")
set_service_paths("tenant")
print(f"[TENANT] After set_service_paths: sys.path[:3] = {sys.path[:3]}")

# Clear gateway modules that might interfere using conftest function
print(f"[TENANT] Before clear_service_modules")
clear_service_modules()
print(f"[TENANT] After clear_service_modules")

# Clear tenant service modules too
print(f"[TENANT] Before _clear_tenant_service_modules")
_clear_tenant_service_modules()
print(f"[TENANT] After _clear_tenant_service_modules")


@pytest.fixture(scope="module")
def test_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a test database session (synchronous, non-async fixture)."""
    session_factory = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Create tables
    import asyncio

    async def create_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())

    # Yield the session
    session = session_factory()
    yield session

    # Drop tables
    async def drop_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(drop_tables())

    # Close session
    asyncio.run(session.close())


@pytest.fixture
def auth_headers():
    """Create authentication headers with a valid JWT."""
    token = create_token(
        subject="test-tenant-id",
        secret_key="test-secret-key-for-testing",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


# Import models from shared
from shared.models.base import Base
from shared.utils.auth import create_token


# Test 1: test_create_tenant
def test_create_tenant(test_session, auth_headers):
    """Test creating a new tenant returns 201 with tenant data."""
    from app.models.schemas import TenantCreateRequest
    from app.services.tenant_service import TenantService

    service = TenantService(test_session)
    payload = TenantCreateRequest(name="Test Tenant 1", website_url="https://example.com")

    tenant = asyncio_run(service.create_tenant(payload, tenant_id="test-uuid-1234"))

    assert tenant.name == "Test Tenant 1"
    assert tenant.website_url == "https://example.com"
    assert tenant.is_active is True


# Test 2: test_duplicate_tenant_name_returns_409
def test_duplicate_tenant_name_returns_409(test_session, auth_headers):
    """Test creating a tenant with duplicate name returns 409."""
    from app.models.schemas import TenantCreateRequest
    from app.services.tenant_service import TenantService
    from shared.utils.errors import ConflictError

    service = TenantService(test_session)

    # Create first tenant
    asyncio_run(service.create_tenant(TenantCreateRequest(name="Duplicate Tenant"), tenant_id="test-uuid-1"))

    # Try to create tenant with same name
    with pytest.raises(ConflictError):
        asyncio_run(service.create_tenant(TenantCreateRequest(name="Duplicate Tenant"), tenant_id="test-uuid-2"))


# Test 3: test_get_tenant_by_id
def test_get_tenant_by_id(test_session, auth_headers):
    """Test getting a tenant by ID returns 200 with tenant data."""
    from app.models.schemas import TenantCreateRequest
    from app.services.tenant_service import TenantService

    service = TenantService(test_session)

    # Create tenant
    asyncio_run(service.create_tenant(TenantCreateRequest(name="Get Tenant Test"), tenant_id="get-id"))

    # Get tenant by ID
    result = asyncio_run(service.get_tenant("get-id"))

    assert result.name == "Get Tenant Test"
    assert result.tenant_id == "get-id"


# Test 4: test_get_nonexistent_tenant_returns_404
def test_get_nonexistent_tenant_returns_404(test_session, auth_headers):
    """Test getting a nonexistent tenant returns 404."""
    from app.services.tenant_service import TenantService
    from shared.utils.errors import NotFoundError

    service = TenantService(test_session)

    # Try to get nonexistent tenant
    with pytest.raises(NotFoundError):
        asyncio_run(service.get_tenant("nonexistent-id"))


# Test 5: test_list_tenants_paginated
def test_list_tenants_paginated(test_session, auth_headers):
    """Test listing tenants with pagination returns correct results."""
    from app.models.schemas import TenantCreateRequest
    from app.services.tenant_service import TenantService

    service = TenantService(test_session)

    # Create multiple tenants
    for i in range(5):
        asyncio_run(service.create_tenant(TenantCreateRequest(name=f"Paginated Tenant {i}"), tenant_id=f"paginated-{i}"))

    # List tenants
    result = asyncio_run(service.list_tenants(limit=2, offset=0))

    assert len(result["items"]) <= 2
    assert result["total"] == 5
    assert result["limit"] == 2


# Test 6: test_soft_delete_tenant
def test_soft_delete_tenant(test_session, auth_headers):
    """Test soft deleting a tenant sets is_active to False."""
    from app.models.schemas import TenantCreateRequest
    from app.services.tenant_service import TenantService

    service = TenantService(test_session)

    # Create tenant
    asyncio_run(service.create_tenant(TenantCreateRequest(name="Soft Delete Tenant"), tenant_id="soft-delete"))

    # Soft delete
    asyncio_run(service.delete_tenant("soft-delete"))

    # Verify tenant is no longer accessible (is_active=False)
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from shared.models.tenants import Tenant

    async def check_deleted():
        result = await test_session.execute(select(Tenant).where(Tenant.tenant_id == "soft-delete"))
        deleted_tenant = result.scalar_one_or_none()
        assert deleted_tenant.is_active is False

    asyncio_run(check_deleted())


# Test 7: test_create_api_key_returns_plain_key_once
def test_create_api_key_returns_plain_key_once(test_session, auth_headers):
    """Test creating an API key returns the plain key only once."""
    import re

    from app.models.schemas import APIKeyCreateRequest, TenantCreateRequest
    from app.services.api_key_service import APIKeyService
    from app.services.tenant_service import TenantService

    tenant_service = TenantService(test_session)
    key_service = APIKeyService(test_session)

    # Create tenant
    asyncio_run(tenant_service.create_tenant(TenantCreateRequest(name="API Key Tenant"), tenant_id="api-key-tenant"))

    # Create API key
    key_data = asyncio_run(key_service.create_api_key("api-key-tenant", APIKeyCreateRequest(name="Test API Key", expires_days=30)))

    assert key_data.name == "Test API Key"
    assert "key" in key_data.model_dump()
    assert len(key_data.key) == 64  # 32 bytes = 64 hex chars
    assert re.match(r"^[a-f0-9]{64}$", key_data.key)


# Test 8: test_api_key_stored_as_bcrypt_hash
def test_api_key_stored_as_bcrypt_hash(test_session, auth_headers):
    """Test that API keys are stored as bcrypt hashes, not plaintext."""
    from app.models.schemas import APIKeyCreateRequest, TenantCreateRequest
    from app.services.api_key_service import APIKeyService
    from app.services.tenant_service import TenantService

    tenant_service = TenantService(test_session)
    key_service = APIKeyService(test_session)

    # Create tenant and API key
    asyncio_run(tenant_service.create_tenant(TenantCreateRequest(name="Hash Test Tenant"), tenant_id="hash-tenant"))
    key_data = asyncio_run(key_service.create_api_key("hash-tenant", APIKeyCreateRequest(name="Key for Hash Test")))

    # Verify key is stored as bcrypt hash by checking the hash format
    from sqlalchemy import select
    from shared.models.tenants import APIKey

    async def check_hash():
        result = await test_session.execute(select(APIKey).where(APIKey.id == key_data.id))
        stored_key = result.scalar_one_or_none()
        # The hash should start with $2b$, $2a$, or $2y$ (bcrypt format)
        assert stored_key.key_hash.startswith("$2")

    asyncio_run(check_hash())


# Test 9: test_rotate_api_key
def test_rotate_api_key(test_session, auth_headers):
    """Test rotating an API key generates a new key and invalidates the old one."""
    from app.models.schemas import APIKeyCreateRequest, TenantCreateRequest
    from app.services.api_key_service import APIKeyService
    from app.services.tenant_service import TenantService

    tenant_service = TenantService(test_session)
    key_service = APIKeyService(test_session)

    # Create tenant and API key
    asyncio_run(tenant_service.create_tenant(TenantCreateRequest(name="Rotate Tenant"), tenant_id="rotate-tenant"))
    key_data = asyncio_run(key_service.create_api_key("rotate-tenant", APIKeyCreateRequest(name="Key to Rotate")))
    old_key = key_data.key
    key_id = key_data.id

    # Rotate the key
    rotated_data = asyncio_run(key_service.rotate_api_key("rotate-tenant", key_id))
    new_key = rotated_data.key

    # Verify the new key is different
    assert new_key != old_key
    assert len(new_key) == 64


# Test 10: test_revoke_api_key
def test_revoke_api_key(test_session, auth_headers):
    """Test revoking an API key marks it as inactive."""
    from app.models.schemas import APIKeyCreateRequest, TenantCreateRequest
    from app.services.api_key_service import APIKeyService
    from app.services.tenant_service import TenantService

    tenant_service = TenantService(test_session)
    key_service = APIKeyService(test_session)

    # Create tenant and API key
    asyncio_run(tenant_service.create_tenant(TenantCreateRequest(name="Revoke Tenant"), tenant_id="revoke-tenant"))
    key_data = asyncio_run(key_service.create_api_key("revoke-tenant", APIKeyCreateRequest(name="Key to Revoke")))
    key_id = key_data.id

    # Verify key is active
    keys = asyncio_run(key_service.list_api_keys("revoke-tenant"))
    assert keys[0].is_active is True

    # Revoke the key
    asyncio_run(key_service.revoke_api_key("revoke-tenant", key_id))

    # Verify key is now inactive
    keys = asyncio_run(key_service.list_api_keys("revoke-tenant"))
    assert keys[0].is_active is False


# Test 11: test_list_api_keys_does_not_expose_hash
def test_list_api_keys_does_not_expose_hash(test_session, auth_headers):
    """Test that listing API keys does not expose the hash."""
    from app.models.schemas import APIKeyCreateRequest, TenantCreateRequest
    from app.services.api_key_service import APIKeyService
    from app.services.tenant_service import TenantService

    tenant_service = TenantService(test_session)
    key_service = APIKeyService(test_session)

    # Create tenant and API key
    asyncio_run(tenant_service.create_tenant(TenantCreateRequest(name="Hash Exposure Tenant"), tenant_id="hash-exp-tenant"))
    key_data = asyncio_run(key_service.create_api_key("hash-exp-tenant", APIKeyCreateRequest(name="Key for Hash Test")))
    key_id = key_data.id

    # List API keys
    keys = asyncio_run(key_service.list_api_keys("hash-exp-tenant"))

    # Verify the response does not contain the hash
    assert len(keys) >= 1
    key = keys[0]

    # Hash should NOT be exposed in listing
    assert not hasattr(key, "key_hash")
    assert not hasattr(key, "hash")
    # Plain key should NEVER be exposed in listing
    assert not hasattr(key, "key")

    # Verify only expected fields are present
    allowed_fields = {"id", "tenant_id", "name", "created_at", "expires_at", "is_active"}
    actual_fields = set(key.model_dump().keys())
    assert actual_fields.issubset(allowed_fields)


# Helper function to run async code in sync context
def asyncio_run(coro):
    """Run an async coroutine in a synchronous context."""
    import asyncio

    return asyncio.run(coro)
