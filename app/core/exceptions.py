"""
Custom exception classes for Stratyon platform.

Provides structured error handling with error codes, user-friendly messages,
and support for request correlation IDs.
"""

from typing import Optional, Dict, Any
from datetime import datetime


class StratyonException(Exception):
    """Base exception for all Stratyon errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)

    def to_dict(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Convert exception to dictionary format for API response."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "request_id": request_id,
                "timestamp": self.timestamp.isoformat(),
            }
        }


class AuthenticationError(StratyonException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details,
        )


class AuthorizationError(StratyonException):
    """Raised when user doesn't have permission."""

    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details,
        )


class RateLimitExceeded(StratyonException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after
        if limit:
            error_details["limit"] = limit

        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=error_details,
        )


class CacheError(StratyonException):
    """Raised when cache operation fails."""

    def __init__(
        self,
        message: str = "Cache operation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="CACHE_ERROR",
            status_code=500,
            details=details,
        )


class ValidationError(StratyonException):
    """Raised when request validation fails."""

    def __init__(
        self,
        message: str = "Validation error",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field

        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=error_details,
        )


class ResourceNotFoundError(StratyonException):
    """Raised when requested resource doesn't exist."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = resource_id

        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=404,
            details=error_details,
        )


class DatabaseError(StratyonException):
    """Raised when database operation fails."""

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if operation:
            error_details["operation"] = operation

        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500,
            details=error_details,
        )


class ExternalServiceError(StratyonException):
    """Raised when external service call fails."""

    def __init__(
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if service_name:
            error_details["service_name"] = service_name

        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details=error_details,
        )


class RefreshTokenError(StratyonException):
    """Raised when refresh token operation fails."""

    def __init__(
        self,
        message: str = "Refresh token error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="REFRESH_TOKEN_ERROR",
            status_code=401,
            details=details,
        )


class TokenExpiredError(StratyonException):
    """Raised when token has expired."""

    def __init__(
        self,
        message: str = "Token has expired",
        token_type: str = "access",
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        error_details["token_type"] = token_type

        super().__init__(
            message=message,
            code="TOKEN_EXPIRED",
            status_code=401,
            details=error_details,
        )


class TokenRevokedError(StratyonException):
    """Raised when token has been revoked."""

    def __init__(
        self,
        message: str = "Token has been revoked",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="TOKEN_REVOKED",
            status_code=401,
            details=details,
        )
