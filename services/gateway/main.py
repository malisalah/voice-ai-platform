"""FastAPI app factory for gateway service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.utils.logging import get_logger, setup_logging

from config import settings

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance
    """
    # Setup logging
    setup_logging(settings.LOG_LEVEL)

    # Create FastAPI app
    app = FastAPI(
        title="Voice AI Gateway Service",
        description="API Gateway for Voice AI Agent Platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        on_shutdown=[cleanup_redis],
    )

    # Include routers
    from app.routers import auth, health, proxy

    app.include_router(auth.router, prefix="", tags=["Authentication"])
    app.include_router(health.router, prefix="", tags=["Health"])
    app.include_router(proxy.router, prefix="", tags=["Proxy"])

    # Register middleware in REVERSE order (FastAPI runs them in reverse):
    # Execution order: CORS -> Auth -> Tenant -> RateLimit
    from app.middleware.auth import AuthMiddleware
    from app.middleware.rate_limit import RateLimitMiddleware
    from app.middleware.tenant import TenantMiddleware

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.GATEWAY_ALLOWED_ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )

    logger.info(
        "Gateway service started",
        port=settings.SERVICE_PORT,
        environment=settings.ENVIRONMENT,
    )

    return app


async def cleanup_redis() -> None:
    """Clean up Redis connection on shutdown."""
    from app.utils.redis import close_redis_client

    await close_redis_client()
    logger.info("Redis connection closed")


# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.ENVIRONMENT == "development",
    )
