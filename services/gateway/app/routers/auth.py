"""Auth router - token exchange and verification endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from shared.utils.errors import AuthError
from shared.utils.logging import get_logger

from app.models.schemas import (
    TokenExchangeRequest,
    TokenExchangeResponse,
    TokenVerifyRequest,
    TokenVerifyResponse,
)
from app.services.auth_service import create_auth_token, extract_tenant_id_from_token

logger = get_logger(__name__)

router = APIRouter()


@router.post("/auth/token", response_model=TokenExchangeResponse)
async def exchange_api_key_for_token(
    request: TokenExchangeRequest,
) -> TokenExchangeResponse:
    """Exchange API key for JWT token.

    Validates the API key and returns a JWT token containing tenant_id.

    Args:
        request: TokenExchangeRequest with api_key

    Returns:
        TokenExchangeResponse with access_token

    Raises:
        HTTPException: If API key is invalid
    """
    try:
        # Extract tenant_id from API key by calling tenant-service
        from app.services.proxy import call_tenant_service

        # API keys are stored hashed, so we need to verify them
        # This assumes tenant-service has a /api-keys/verify endpoint
        result = await call_tenant_service(
            method="POST",
            path="/api-keys/verify",
            body={"api_key": request.api_key},
        )

        tenant_id = result.get("tenant_id")
        if not tenant_id:
            raise AuthError("Invalid API key")

        # Create JWT token with tenant_id
        token = create_auth_token(tenant_id)

        return TokenExchangeResponse(access_token=token, expires_in=3600)

    except AuthError as exc:
        return JSONResponse(
            status_code=401,
            content={"error": str(exc)},
        )
    except Exception as exc:
        logger.error("Token exchange failed", error=str(exc))
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid API key"},
        )


@router.post("/auth/verify", response_model=TokenVerifyResponse)
async def verify_token_endpoint(
    request: TokenVerifyRequest,
) -> TokenVerifyResponse:
    """Verify a JWT token is valid.

    Args:
        request: TokenVerifyRequest with token

    Returns:
        TokenVerifyResponse with validity info
    """
    try:
        tenant_id = extract_tenant_id_from_token(request.token)

        return TokenVerifyResponse(
            valid=True,
            tenant_id=tenant_id,
        )

    except AuthError as exc:
        return TokenVerifyResponse(
            valid=False,
            error=str(exc),
        )
