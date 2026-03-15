"""FastAPI app factory for tenant-service."""

import logging

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.db.base import init_models
from shared.utils.errors import APIError

from config import settings

# Configure structlog for structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.SERVICE_NAME,
        version="1.0.0",
        description="Tenant Management Service - Manages tenants and API keys",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    from app.routers import tenants, api_keys

    app.include_router(tenants.router)
    app.include_router(api_keys.router)

    # Startup event
    @app.on_event("startup")
    async def on_startup() -> None:
        """Initialize database models on startup."""
        logger.info("Starting up tenant-service")
        try:
            await init_models()
            logger.info("Database models initialized")
        except Exception as exc:
            logger.error("Failed to initialize database", error=str(exc))

    # Shutdown event
    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        """Cleanup on shutdown."""
        logger.info("Shutting down tenant-service")

    # Exception handlers
    @app.exception_handler(APIError)
    async def api_error_handler(request, exc: APIError) -> JSONResponse:
        """Handle API errors."""
        logger.warning(
            "API error",
            message=exc.message,
            code=exc.code,
            status_code=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request, exc: Exception) -> JSONResponse:
        """Handle unexpected errors."""
        logger.error("Unexpected error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )

    return app


# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.ENVIRONMENT == "development",
    )
