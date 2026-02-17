"""
Global error handler middleware for structured error responses.
"""

import logging
import traceback
import uuid
from typing import Union

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import StratyonException

logger = logging.getLogger(__name__)


async def stratyon_exception_handler(
    request: Request, exc: StratyonException
) -> JSONResponse:
    """
    Handler for custom Stratyon exceptions.
    Returns structured error response with request ID.
    """
    request_id = request.state.request_id if hasattr(request.state, "request_id") else str(uuid.uuid4())

    logger.error(
        f"StratyonException: {exc.code} - {exc.message}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(request_id=request_id),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handler for standard HTTP exceptions.
    Converts to structured error format.
    """
    request_id = request.state.request_id if hasattr(request.state, "request_id") else str(uuid.uuid4())

    logger.warning(
        f"HTTPException: {exc.status_code} - {exc.detail}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "request_id": request_id,
            }
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handler for request validation errors.
    Returns detailed field-level errors.
    """
    request_id = request.state.request_id if hasattr(request.state, "request_id") else str(uuid.uuid4())

    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(
        f"ValidationError: {len(errors)} validation errors",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "errors": errors,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": errors},
                "request_id": request_id,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for unexpected exceptions.
    Logs full traceback and returns generic error to client.
    """
    request_id = request.state.request_id if hasattr(request.state, "request_id") else str(uuid.uuid4())

    # Log full traceback
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc(),
        },
        exc_info=True,
    )

    # Return generic error to client (don't expose internal details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "request_id": request_id,
            }
        },
    )
