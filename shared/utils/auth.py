"""JWT encode/decode helpers using python-jose."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwe, jwt

from shared.utils.errors import AuthError

# Default JWT settings
DEFAULT_ALGORITHM = "HS256"
DEFAULT_TOKEN_EXPIRY_MINUTES = 60
DEFAULT_REFRESH_TOKEN_EXPIRY_DAYS = 7


def create_token(
    subject: str,
    expires_minutes: int = DEFAULT_TOKEN_EXPIRY_MINUTES,
    additional_claims: Optional[Dict[str, Any]] = None,
    secret_key: Optional[str] = None,
    algorithm: str = DEFAULT_ALGORITHM,
) -> str:
    """Create a signed JWT token.

    Args:
        subject: The subject of the token (e.g., user_id, tenant_id)
        expires_minutes: Token expiry time in minutes
        additional_claims: Optional additional claims to include
        secret_key: Secret key for signing (defaults to PLATFORM_SECRET_KEY)
        algorithm: Signing algorithm (default: HS256)

    Returns:
        Signed JWT token string
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)

    claims = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "jti": secrets.token_hex(16),
    }

    if additional_claims:
        claims.update(additional_claims)

    return jwt.encode(claims, secret_key or "", algorithm=algorithm)


def decode_token(
    token: str,
    secret_key: Optional[str] = None,
    algorithms: list[str] = None,
) -> Dict[str, Any]:
    """Decode and verify a JWT token.

    Args:
        token: The JWT token string
        secret_key: Secret key for verification
        algorithms: List of allowed algorithms

    Returns:
        Decoded claims dictionary

    Raises:
        AuthError: If token is invalid or expired
    """
    if algorithms is None:
        algorithms = [DEFAULT_ALGORITHM]

    try:
        return jwt.decode(token, secret_key or "", algorithms=algorithms)
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token has expired") from exc
    except jwt.JWTError as exc:
        raise AuthError("Invalid token") from exc


def create_refresh_token(
    subject: str,
    expires_days: int = DEFAULT_REFRESH_TOKEN_EXPIRY_DAYS,
    additional_claims: Optional[Dict[str, Any]] = None,
    secret_key: Optional[str] = None,
) -> str:
    """Create a refresh token with longer expiry.

    Args:
        subject: The subject of the token
        expires_days: Token expiry time in days
        additional_claims: Optional additional claims
        secret_key: Secret key for signing

    Returns:
        Signed refresh token string
    """
    return create_token(
        subject=subject,
        expires_minutes=expires_days * 24 * 60,
        additional_claims=additional_claims,
        secret_key=secret_key,
    )


def verify_token(
    token: str,
    secret_key: Optional[str] = None,
) -> bool:
    """Verify if a token is valid without raising exceptions.

    Args:
        token: The JWT token string
        secret_key: Secret key for verification

    Returns:
        True if token is valid, False otherwise
    """
    try:
        decode_token(token, secret_key)
        return True
    except AuthError:
        return False
