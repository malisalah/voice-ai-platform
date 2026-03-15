"""HTTP proxy service for forwarding requests to backend services."""

import os
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from shared.utils.errors import (
    ServiceError,
    NotFoundError,
    AuthorizationError,
    ValidationError,
)
from shared.utils.logging import get_logger

logger = get_logger(__name__)


def get_service_url(service_name: str) -> str:
    """Get service URL from environment variable at runtime.

    Args:
        service_name: Name of the service (tenant, voice, llm, knowledge, crawler)

    Returns:
        Service URL from environment or default
    """
    defaults = {
        "tenant": "http://tenant-service:8005",
        "voice": "http://voice-service:8001",
        "llm": "http://llm-service:8002",
        "knowledge": "http://knowledge-service:8003",
        "crawler": "http://crawler-service:8004",
    }
    env_var = f"{service_name.upper()}_SERVICE_URL"
    return os.getenv(env_var, defaults[service_name])


def get_backend_url(path: str) -> Optional[str]:
    """Get the backend service URL for a given path.

    Args:
        path: The request path (e.g., /api/tenants/123)

    Returns:
        Backend service URL or None if no match
    """
    prefixes = {
        "/api/tenants": get_service_url("tenant"),
        "/api/knowledge": get_service_url("knowledge"),
        "/api/crawl": get_service_url("crawler"),
        "/api/llm": get_service_url("llm"),
        "/api/voice": get_service_url("voice"),
    }
    for prefix, url in prefixes.items():
        if path.startswith(prefix):
            return url
    return None


def rewrite_path(path: str, prefix: str) -> str:
    """Remove the API prefix from the path.

    Args:
        path: The full request path
        prefix: The prefix to remove (e.g., /api/tenants)

    Returns:
        The rewritten path (e.g., /tenants/123)
    """
    return path[len(prefix) :] if path.startswith(prefix) else path


async def proxy_request(
    method: str,
    path: str,
    headers: Dict[str, str],
    body: Optional[Dict[str, Any]] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Proxy request to the appropriate backend service.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        headers: Request headers
        body: Request body (optional)
        tenant_id: Tenant ID from JWT (optional, will add to headers)

    Returns:
        Response dict with status_code, headers, and body

    Raises:
        HTTPException: If backend service returns an error
    """
    backend_url = get_backend_url(path)
    if not backend_url:
        raise HTTPException(status_code=404, detail="Service not found")

    # Build the target URL - find the correct prefix and rewrite path
    prefix = None
    for p in ["/api/tenants", "/api/knowledge", "/api/crawl", "/api/llm", "/api/voice"]:
        if path.startswith(p):
            prefix = p
            break
    rewritten_path = rewrite_path(path, prefix) if prefix else path
    target_url = f"{backend_url}{rewritten_path}"

    # Prepare headers - preserve important headers
    proxy_headers = {
        k: v
        for k, v in headers.items()
        if k.lower()
        not in [
            "host",
            "content-length",
            "connection",
        ]
    }

    # Add tenant_id header if available
    if tenant_id:
        proxy_headers["x-tenant-id"] = tenant_id

    logger.info(
        "Proxying request",
        method=method,
        path=path,
        target_url=target_url,
        tenant_id=tenant_id,
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=proxy_headers,
                json=body,
            )

            # Parse response body
            try:
                response_body = response.json()
            except (ValueError, httpx.DecodingError):
                response_body = {"raw": response.text[:500]}

            return {
                "status_code": response.status_code,
                "headers": getattr(response, "headers", {}),
                "body": response_body,
            }

    except httpx.TimeoutException:
        logger.error(
            "Backend service timeout",
            target_url=target_url,
            method=method,
        )
        raise ServiceError(
            message=f"Backend service timeout",
            service=get_service_name(target_url),
        )

    except httpx.ConnectError:
        logger.error(
            "Backend service connection error",
            target_url=target_url,
            method=method,
        )
        raise ServiceError(
            message=f"Backend service unavailable",
            service=get_service_name(target_url),
        )

    except httpx.HTTPStatusError as exc:
        logger.error(
            "Backend service error",
            target_url=target_url,
            status_code=exc.response.status_code,
            error=exc.response.text,
        )
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        )


def get_service_name(url: str) -> str:
    """Get service name from URL for error messages."""
    if "tenant-service" in url:
        return "tenant-service"
    elif "voice-service" in url:
        return "voice-service"
    elif "llm-service" in url:
        return "llm-service"
    elif "knowledge-service" in url:
        return "knowledge-service"
    elif "crawler-service" in url:
        return "crawler-service"
    return "unknown-service"


async def call_tenant_service(
    method: str,
    path: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Helper to call tenant-service directly.

    Args:
        method: HTTP method
        path: Path relative to tenant-service root
        headers: Additional headers
        body: Request body

    Returns:
        Response body dict
    """
    full_path = f"{get_service_url('tenant')}{path}"
    proxy_headers = headers or {}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(
                method=method,
                url=full_path,
                headers=proxy_headers,
                json=body,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise NotFoundError(f"Tenant service: {exc.response.text}")
        raise ServiceError(
            message=f"Tenant service error: {exc.response.text}",
            service="tenant-service",
        )
