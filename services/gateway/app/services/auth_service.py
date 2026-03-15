"""Authentication service for gateway - JWT validation and tenant extraction."""

import os
from typing import Optional

from shared.utils.auth import decode_token, create_token
from shared.utils.errors import AuthError, NotFoundError
from shared.utils.logging import get_logger

from app.services.proxy import call_tenant_service

logger = get_logger(__name__)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
DEFAULT_TOKEN_EXPIRY_MINUTES = 60


def extract_tenant_id_from_token(token: str) -> str:
    """Extract tenant_id from JWT token.

    Args:
        token: JWT token string

    Returns:
        tenant_id from token claims

    Raises:
        AuthError: If token is invalid or tenant_id is missing
    """
    if not JWT_SECRET_KEY:
        raise AuthError("JWT_SECRET_KEY not configured")

    try:
        claims = decode_token(token, JWT_SECRET_KEY)
    except AuthError as exc:
        logger.warning("Invalid token provided", error=str(exc))
        raise AuthError("Invalid or expired token") from exc

    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        logger.warning("Token missing tenant_id claim")
        raise AuthError("Token does not contain tenant_id")

    return tenant_id


def create_auth_token(tenant_id: str, expires_minutes: int = DEFAULT_TOKEN_EXPIRY_MINUTES) -> str:
    """Create a JWT token for a tenant.

    Args:
        tenant_id: The tenant ID to encode in the token
        expires_minutes: Token expiry time in minutes

    Returns:
        Signed JWT token string
    """
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY not configured")

    claims = {"tenant_id": tenant_id}
    return create_token(
        subject=tenant_id,
        expires_minutes=expires_minutes,
        additional_claims=claims,
        secret_key=JWT_SECRET_KEY,
    )


async def validate_api_key(tenant_id: str, api_key: str) -> bool:
    """Validate an API key against tenant-service.

    Args:
        tenant_id: The tenant ID
        api_key: The API key to validate (plain 64-char hex)

    Returns:
        True if API key is valid, False otherwise
    """
    try:
        result = await call_tenant_service(
            method="GET",
            path=f"/api-keys/validate/{tenant_id}",
            headers={"x-api-key": api_key},
        )
        return result.get("valid", False)
    except Exception as exc:
        logger.error("API key validation failed", error=str(exc))
        return False


async def verify_api_key_for_tenant(tenant_id: str, api_key: str) -> bool:
    """Verify API key belongs to tenant and is valid.

    Calls tenant-service to verify the API key hash matches.

    Args:
        tenant_id: The tenant ID
        api_key: The plain API key to verify

    Returns:
        True if API key is valid for tenant, False otherwise
    """
    try:
        result = await call_tenant_service(
            method="POST",
            path="/api-keys/verify",
            body={"tenant_id": tenant_id, "api_key": api_key},
        )
        return result.get("valid", False)
    except NotFoundError:
        return False
    except Exception as exc:
        logger.error("API key verification failed", tenant_id=tenant_id, error=str(exc))
        return False
