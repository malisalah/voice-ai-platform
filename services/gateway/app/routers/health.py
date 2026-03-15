"""Health check router - checks status of all downstream services."""

import asyncio
import time
from typing import List

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from shared.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Backend service URLs from environment
TENANT_SERVICE_URL = "http://tenant-service:8005"
VOICE_SERVICE_URL = "http://voice-service:8001"
LLM_SERVICE_URL = "http://llm-service:8002"
KNOWLEDGE_SERVICE_URL = "http://knowledge-service:8003"
CRAWLER_SERVICE_URL = "http://crawler-service:8004"

SERVICES = {
    "tenant-service": TENANT_SERVICE_URL,
    "voice-service": VOICE_SERVICE_URL,
    "llm-service": LLM_SERVICE_URL,
    "knowledge-service": KNOWLEDGE_SERVICE_URL,
    "crawler-service": CRAWLER_SERVICE_URL,
}


async def check_service_health(name: str, url: str) -> dict:
    """Check health of a single service.

    Args:
        name: Service name
        url: Service URL

    Returns:
        Health check result dict
    """
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/health")
            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return {
                    "service": name,
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 2),
                }
            else:
                return {
                    "service": name,
                    "status": "degraded",
                    "latency_ms": round(latency_ms, 2),
                    "error": f"Status {response.status_code}",
                }

    except httpx.TimeoutException:
        return {
            "service": name,
            "status": "unhealthy",
            "error": "Timeout",
        }
    except httpx.ConnectionError:
        return {
            "service": name,
            "status": "unhealthy",
            "error": "Connection refused",
        }
    except Exception as exc:
        return {
            "service": name,
            "status": "unhealthy",
            "error": str(exc),
        }


@router.get("/health")
async def health_check() -> JSONResponse:
    """Check health of all downstream services.

    Returns:
        200 with overall health status if all services healthy
        503 if any service is unhealthy
    """
    # Check all services in parallel
    tasks = [
        check_service_health(name, url)
        for name, url in SERVICES.items()
    ]
    results = await asyncio.gather(*tasks)

    # Determine overall status
    statuses = [r["status"] for r in results]
    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
        status_code = 200
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
        status_code = 503
    else:
        overall_status = "degraded"
        status_code = 200

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "services": results,
        },
    )


@router.get("/health/{service}")
async def single_service_health(service: str) -> JSONResponse:
    """Check health of a single service.

    Args:
        service: Service name

    Returns:
        Health check result for the specified service
    """
    url = SERVICES.get(service)
    if not url:
        return JSONResponse(
            status_code=404,
            content={
                "error": f"Unknown service: {service}",
                "available_services": list(SERVICES.keys()),
            },
        )

    result = await check_service_health(service, url)

    status_code = 200 if result["status"] == "healthy" else 503

    return JSONResponse(
        status_code=status_code,
        content=result,
    )
