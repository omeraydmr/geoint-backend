"""
Rate limiting configuration for Stratyon platform.

Implements plan-based rate limiting using slowapi and Redis.
"""

import logging
from typing import Optional
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)


# Plan-based rate limits (requests per hour)
RATE_LIMITS = {
    "free": "50/hour",
    "insight": "100/hour",
    "strategy": "500/hour",
    "growth": "1000/hour",
    "enterprise": "10000/hour",  # Effectively unlimited
}


async def get_user_plan_rate_limit(request: Request) -> str:
    """
    Get rate limit key based on user's subscription plan.

    Extracts user from JWT token and returns plan-based rate limit.
    Falls back to IP-based limiting for unauthenticated requests.

    Returns:
        Rate limit string (e.g., "100/hour")
    """
    try:
        # Try to get authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            # No token - use strict rate limit for anonymous users
            logger.debug("No auth token found, using anonymous rate limit")
            return "50/hour"

        # Extract token
        token = auth_header.split(" ")[1]

        # Decode token to get user info
        payload = decode_access_token(token)
        user_plan = payload.get("plan", "free")

        # Get rate limit for plan
        rate_limit = RATE_LIMITS.get(user_plan, RATE_LIMITS["free"])

        logger.debug(f"Rate limit for plan '{user_plan}': {rate_limit}")
        return rate_limit

    except Exception as e:
        # If any error occurs, fall back to free tier limit
        logger.warning(f"Error determining rate limit: {e}, using free tier limit")
        return RATE_LIMITS["free"]


async def get_user_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.

    Uses user_id from JWT if available, otherwise falls back to IP address.

    Returns:
        Unique identifier string
    """
    try:
        # Try to get authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            # No token - use IP address
            return get_remote_address(request)

        # Extract token
        token = auth_header.split(" ")[1]

        # Decode token to get user info
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        user_plan = payload.get("plan", "free")

        if user_id:
            # Return identifier with plan for better tracking
            return f"user:{user_id}:plan:{user_plan}"

        # Fall back to IP if no user_id
        return get_remote_address(request)

    except Exception as e:
        # If any error occurs, fall back to IP address
        logger.warning(f"Error getting user identifier: {e}")
        return get_remote_address(request)


# Initialize rate limiter
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["1000/hour"],  # Global default
    storage_uri=settings.REDIS_URL,
    strategy="fixed-window",
    headers_enabled=True,  # Add X-RateLimit-* headers to responses
)


def get_rate_limit_for_endpoint(endpoint_type: str = "standard") -> str:
    """
    Get rate limit string for specific endpoint type.

    Args:
        endpoint_type: Type of endpoint ("standard", "expensive", "public")

    Returns:
        Rate limit string
    """
    endpoint_limits = {
        "public": "100/hour",  # Public endpoints (no auth)
        "standard": "dynamic",  # Standard endpoints (plan-based)
        "expensive": "10/minute",  # Expensive operations (GEOINT calculations)
        "health": "1000/hour",  # Health checks (high limit)
    }

    return endpoint_limits.get(endpoint_type, "dynamic")
