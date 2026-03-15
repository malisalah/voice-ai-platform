"""CORS middleware for gateway."""

import os

from fastapi.middleware.cors import CORSMiddleware

from shared.utils.logging import get_logger

logger = get_logger(__name__)

# Allowed origins from environment
ALLOWED_ORIGINS = os.getenv(
    "GATEWAY_ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8006",
)
ALLOWED_ORIGINS_LIST = [
    origin.strip()
    for origin in ALLOWED_ORIGINS.split(",")
    if origin.strip()
]

logger.info("CORS configured", allowed_origins=ALLOWED_ORIGINS_LIST)

cors_middleware = CORSMiddleware(
    allow_origins=ALLOWED_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
