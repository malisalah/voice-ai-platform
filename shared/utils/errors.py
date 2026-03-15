"""Custom exception classes following FastAPI conventions."""

from http import HTTPStatus
from typing import Any, Dict, Optional


class APIError(Exception):
    """Base exception for all API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = HTTPStatus.BAD_REQUEST,
        code: str = "API_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(APIError):
    """Exception raised when authentication fails."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNAUTHORIZED,
            code="AUTHENTICATION_ERROR",
        )


class AuthorizationError(APIError):
    """Exception raised when authorization fails."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=HTTPStatus.FORBIDDEN,
            code="AUTHORIZATION_ERROR",
        )


class NotFoundError(APIError):
    """Exception raised when a resource is not found."""

    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"

        super().__init__(
            message=message,
            status_code=HTTPStatus.NOT_FOUND,
            code="NOT_FOUND_ERROR",
        )


class ValidationError(APIError):
    """Exception raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        details = {}
        if field:
            details["field"] = field

        super().__init__(
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
            code="VALIDATION_ERROR",
            details=details,
        )


class ConflictError(APIError):
    """Exception raised when there's a resource conflict."""

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(
            message=message,
            status_code=HTTPStatus.CONFLICT,
            code="CONFLICT_ERROR",
        )


class RateLimitExceededError(APIError):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
        )


class AuthError(APIError):
    """Exception for authentication/authorization related errors."""

    def __init__(self, message: str = "Authentication error"):
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNAUTHORIZED,
            code="AUTH_ERROR",
        )


class DatabaseError(APIError):
    """Exception raised when database operation fails."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DATABASE_ERROR",
        )


class ServiceError(APIError):
    """Exception raised when an external service fails."""

    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        status_code: int = HTTPStatus.SERVICE_UNAVAILABLE,
    ):
        if service:
            message = f"{service}: {message}"

        super().__init__(
            message=message,
            status_code=status_code,
            code="SERVICE_ERROR",
        )
