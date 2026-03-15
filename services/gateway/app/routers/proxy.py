"""Reverse proxy router - forwards requests to backend services."""

from typing import Any, Dict

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from shared.utils.logging import get_logger

from app.services.proxy import proxy_request, get_backend_url

logger = get_logger(__name__)

router = APIRouter()


@router.api_route(
    "/api/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    response_model=None,
)
async def proxy_to_backend(
    request: Request,
    service: str,
    path: str,
) -> Response:
    """Proxy requests to backend services based on path.

    Routes:
        /api/tenants/*     -> tenant-service:8005
        /api/knowledge/*   -> knowledge-service:8003
        /api/crawl/*       -> crawler-service:8004
        /api/llm/*         -> llm-service:8002
        /api/voice/*       -> voice-service:8001

    Args:
        request: FastAPI request object
        service: Service name (tenants, knowledge, crawl, llm, voice)
        path: Path within the service

    Returns:
        Response from backend service
    """
    # Build full path for the backend
    full_path = f"/api/{service}/{path}"

    # Get backend URL to verify service exists
    backend_url = get_backend_url(full_path)
    if not backend_url:
        return JSONResponse(
            status_code=404,
            content={"error": f"Unknown service: {service}"},
        )

    # Extract body
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except Exception:
            body = None

    # Proxy the request
    try:
        result = await proxy_request(
            method=request.method,
            path=full_path,
            headers=dict(request.headers),
            body=body,
            tenant_id=getattr(request.state, "tenant_id", None),
        )

        return Response(
            content=result.get("raw_body") or str(result.get("body", "")),
            status_code=result["status_code"],
            headers=result["headers"],
        )

    except Exception as exc:
        logger.error(
            "Proxy request failed",
            service=service,
            path=path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=502,
            content={
                "error": "Bad Gateway",
                "message": f"Failed to reach {service} service",
            },
        )


@router.get("/api/services")
async def list_backend_services() -> Dict[str, str]:
    """List available backend services and their URLs.

    Returns:
        Dict mapping service names to URLs
    """
    return {
        "tenants": "http://tenant-service:8005",
        "voice": "http://voice-service:8001",
        "llm": "http://llm-service:8002",
        "knowledge": "http://knowledge-service:8003",
        "crawl": "http://crawler-service:8004",
    }
