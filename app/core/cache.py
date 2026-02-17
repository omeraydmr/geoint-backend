"""
Redis caching layer for Stratyon platform.

Provides decorator-based caching with automatic serialization,
TTL management, and cache invalidation strategies.
"""

import json
import hashlib
import logging
from typing import Optional, Any, Callable
from functools import wraps

import redis.asyncio as redis
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.exceptions import CacheError

logger = logging.getLogger(__name__)
settings = get_settings()

# Global Redis client
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client instance."""
    global _redis_client

    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )
            # Test connection
            await _redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise CacheError(f"Redis connection failed: {str(e)}")

    return _redis_client


async def close_redis_client():
    """Close Redis client connection."""
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


def _generate_cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments."""
    # Create a string representation of all arguments
    key_parts = []

    for arg in args:
        if isinstance(arg, BaseModel):
            key_parts.append(arg.model_dump_json())
        elif hasattr(arg, "__dict__"):
            # Skip database sessions and similar objects
            continue
        else:
            key_parts.append(str(arg))

    for k, v in sorted(kwargs.items()):
        if isinstance(v, BaseModel):
            key_parts.append(f"{k}:{v.model_dump_json()}")
        elif hasattr(v, "__dict__"):
            continue
        else:
            key_parts.append(f"{k}:{v}")

    # Hash the combined key parts
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def _serialize(value: Any) -> str:
    """Serialize value for caching."""
    if isinstance(value, BaseModel):
        return value.model_dump_json()
    elif isinstance(value, list):
        # Check if list contains Pydantic models
        if value and isinstance(value[0], BaseModel):
            # Serialize list of Pydantic models.
            # model_dump() returns raw Python objects (including datetime),
            # so default=str is required to handle non-JSON-native types.
            return json.dumps([item.model_dump() for item in value], default=str)
        else:
            return json.dumps(value, default=str)
    elif isinstance(value, dict):
        return json.dumps(value, default=str)
    else:
        return json.dumps(value, default=str)


def _deserialize(value: str, return_type: Optional[type] = None) -> Any:
    """Deserialize cached value."""
    try:
        data = json.loads(value)

        # If return type is a Pydantic model, validate it
        if return_type and issubclass(return_type, BaseModel):
            return return_type.model_validate(data)

        return data
    except json.JSONDecodeError:
        # Return as string if not JSON
        return value


def cache(
    ttl: int = 300,
    key_prefix: str = "",
    enabled: Optional[bool] = None,
):
    """
    Decorator for caching function results in Redis.

    Args:
        ttl: Time-to-live in seconds (default: 5 minutes)
        key_prefix: Prefix for cache keys
        enabled: Override global cache setting (default: use settings.CACHE_ENABLED)

    Usage:
        @cache(ttl=900, key_prefix="geoint:heatmap")
        async def get_heatmap(keyword_id: str):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if caching is enabled
            cache_enabled = enabled if enabled is not None else settings.CACHE_ENABLED

            if not cache_enabled:
                # Skip caching, execute function directly
                return await func(*args, **kwargs)

            try:
                # Generate cache key
                arg_hash = _generate_cache_key(*args, **kwargs)
                cache_key = f"{key_prefix}:{arg_hash}" if key_prefix else arg_hash

                # Get Redis client
                redis_client = await get_redis_client()

                # Try to get from cache
                cached_value = await redis_client.get(cache_key)

                if cached_value:
                    logger.debug(f"Cache HIT: {cache_key}")
                    # Deserialize and return cached value
                    return _deserialize(cached_value)

                # Cache miss - execute function
                logger.debug(f"Cache MISS: {cache_key}")
                result = await func(*args, **kwargs)

                # Store in cache
                serialized = _serialize(result)
                await redis_client.setex(cache_key, ttl, serialized)

                return result

            except CacheError:
                # If cache fails, fall back to executing function
                logger.warning(f"Cache error, executing function directly: {func.__name__}")
                return await func(*args, **kwargs)

            except Exception as e:
                # Log error but don't fail the request
                logger.error(f"Unexpected cache error: {e}")
                return await func(*args, **kwargs)

        return wrapper

    return decorator


async def cache_get(key: str) -> Optional[Any]:
    """Get value from cache."""
    try:
        redis_client = await get_redis_client()
        value = await redis_client.get(key)
        return _deserialize(value) if value else None
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 300):
    """Set value in cache."""
    try:
        redis_client = await get_redis_client()
        serialized = _serialize(value)
        await redis_client.setex(key, ttl, serialized)
    except Exception as e:
        logger.error(f"Cache set error: {e}")


async def cache_delete(key: str):
    """Delete specific key from cache."""
    try:
        redis_client = await get_redis_client()
        await redis_client.delete(key)
        logger.debug(f"Cache key deleted: {key}")
    except Exception as e:
        logger.error(f"Cache delete error: {e}")


async def cache_invalidate(pattern: str):
    """
    Invalidate cache keys matching pattern.

    Args:
        pattern: Redis key pattern (e.g., "geoint:heatmap:*")

    Usage:
        await cache_invalidate("geoint:heatmap:uuid:*")
    """
    try:
        redis_client = await get_redis_client()

        # Find all keys matching pattern
        keys = []
        async for key in redis_client.scan_iter(match=pattern, count=100):
            keys.append(key)

        # Delete all matching keys
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys matching: {pattern}")

    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")


async def cache_clear():
    """Clear all cache (use with caution in production)."""
    try:
        redis_client = await get_redis_client()
        await redis_client.flushdb()
        logger.warning("All cache cleared")
    except Exception as e:
        logger.error(f"Cache clear error: {e}")


async def cache_stats() -> dict:
    """Get cache statistics."""
    try:
        redis_client = await get_redis_client()
        info = await redis_client.info()

        return {
            "keys": await redis_client.dbsize(),
            "memory_used": info.get("used_memory_human"),
            "memory_peak": info.get("used_memory_peak_human"),
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                info.get("keyspace_hits", 0)
                / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                * 100
            ),
        }
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return {}
