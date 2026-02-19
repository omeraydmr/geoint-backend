"""Main FastAPI application for STRATYON"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.cache import get_redis_client, close_redis_client
from app.core.seed import seed_geographic_data
from app.core.exceptions import StratyonException
from app.core.rate_limiter import limiter
from app.core.security import decode_access_token
from app.middleware.error_handler import (
    stratyon_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.middleware.logging import RequestLoggingMiddleware, CorrelationIDMiddleware
from app.websocket.manager import manager as ws_manager
from app.scheduler import start_scheduler, stop_scheduler
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# Import all models so they're registered with SQLAlchemy before init_db
from app.models import (  # noqa: F401
    User, RefreshToken, Keyword, Competitor, CompetitorSnapshot, CompetitorComparisonHistory,
    Strategy, StrategyWeek, StrategyTask,
    MediaMention, PROpportunity,
    Province, District, Neighborhood, GEOINTScore,
    Activity,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print("🚀 Starting STRATYON application...")
    await init_db()
    print("✅ Database initialized")

    # Auto-seed geographic data if tables are empty
    try:
        await seed_geographic_data()
        print("✅ Geographic data check complete")
    except Exception as e:
        print(f"⚠️ Geographic seeding failed: {e}")

    # Initialize Redis connection for caching
    if settings.CACHE_ENABLED:
        try:
            await get_redis_client()
            print("✅ Redis cache initialized")
        except Exception as e:
            print(f"⚠️ Redis cache initialization failed: {e}")
            print("⚠️ Application will run without caching")

    # Verify DataForSEO API connectivity (zero-credit diagnostic)
    try:
        from app.services.external.dataforseo import DataForSEOClient
        async with DataForSEOClient() as dfs_client:
            dfs_ok = await dfs_client.check_connectivity()
            if dfs_ok:
                print("DataForSEO API connectivity verified")
            else:
                print("DataForSEO API unreachable or credentials invalid -- SERP data will use fallback")
    except Exception as e:
        print(f"DataForSEO connectivity check failed: {e}")

    # Start APScheduler for background tasks
    try:
        await start_scheduler()
        print("APScheduler started")
    except Exception as e:
        print(f"APScheduler startup failed: {e}")
        print("Background tasks will not run")

    yield

    # Shutdown
    print("🛑 Shutting down STRATYON application...")

    # Stop scheduler first
    try:
        await stop_scheduler()
        print("✅ APScheduler stopped")
    except Exception as e:
        print(f"⚠️ Error stopping scheduler: {e}")

    await close_db()
    print("✅ Database connections closed")

    # Close Redis connection
    if settings.CACHE_ENABLED:
        await close_redis_client()
        print("✅ Redis cache closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
# STRATYON GEO Intelligence Platform API

Strategic Intelligence Platform for the Turkish Market with Geographic Intelligence (GEOINT).

## Features

- **Geographic Intelligence (GEOINT):** Regional opportunity analysis for 81 provinces, 970 districts
- **Keyword Research:** SEO keyword research with regional trends and metrics
- **Competitor Tracking:** Monitor competitors with domain metrics and keyword analysis
- **Media Monitoring:** Track media mentions and PR opportunities
- **AI Strategy Generation:** AI-powered 90-day marketing strategy planning

## Authentication

All endpoints require JWT Bearer authentication unless marked as public.

1. **Register:** POST `/api/v1/auth/register`
2. **Login:** POST `/api/v1/auth/login` - Returns access_token and refresh_token
3. **Use Token:** Add header `Authorization: Bearer <access_token>`
4. **Refresh Token:** POST `/api/v1/auth/refresh` with refresh_token

## Rate Limiting

Rate limits are plan-based:
- **Free:** 50 requests/hour
- **Insight:** 100 requests/hour
- **Strategy:** 500 requests/hour
- **Growth:** 1000 requests/hour
- **Enterprise:** Unlimited

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Time when limit resets

## Caching

GET endpoints are cached for optimal performance:
- GEOINT endpoints: 15 minutes
- User profile: 10 minutes
- Keyword/Competitor data: 5-10 minutes

## Real-time Updates

WebSocket endpoint for live updates:
- **Endpoint:** `ws://localhost:8000/ws/{access_token}`
- **Events:** GEOINT updates, competitor changes, media mentions, task notifications

## Response Format

All endpoints return JSON. Error responses follow this format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "request_id": "uuid",
    "timestamp": "ISO-8601"
  }
}
```
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "STRATYON Support",
        "email": "support@stratyon.com",
    },
    license_info={
        "name": "Proprietary",
    },
)

# Configure middleware - order matters!
# Proxy headers middleware (trust X-Forwarded-Proto from Caddy for correct HTTPS redirects)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# Request logging middleware (first to capture all requests)
app.add_middleware(RequestLoggingMiddleware)

# Correlation ID middleware
app.add_middleware(CorrelationIDMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Correlation-ID"],
)

# Add rate limiter state
app.state.limiter = limiter

# Register exception handlers
app.add_exception_handler(RateLimitExceeded, stratyon_exception_handler)
app.add_exception_handler(StratyonException, stratyon_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        content={
            "status": "healthy",
            "app": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0",
        }
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to STRATYON API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# WebSocket endpoint for real-time updates
@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket endpoint for real-time updates.

    Clients connect with JWT token in URL for authentication.
    Events: GEOINT updates, competitor changes, media mentions, task notifications
    """
    user_id = None

    try:
        # Authenticate via JWT token
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return

        # Connect user
        await ws_manager.connect(websocket, user_id)
        logger.info(f"WebSocket connected: user_id={user_id}")

        # Send welcome message
        await websocket.send_json({
            "event_type": "connected",
            "message": "WebSocket connection established",
            "user_id": user_id,
        })

        try:
            # Keep connection alive and handle messages
            while True:
                # Receive messages (e.g., ping/pong for keepalive)
                data = await websocket.receive_text()

                # Echo back ping as pong
                if data == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": str(datetime.utcnow().isoformat()),
                    })

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: user_id={user_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket.client_state.name == "CONNECTED":
            await websocket.close(code=1011, reason="Internal error")

    finally:
        # Clean up connection
        if user_id:
            await ws_manager.disconnect(websocket, user_id)


# API v1 router
from app.api.v1.router import api_router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
