"""
API v1 Router Configuration

Python FastAPI Backend - All endpoints
Consolidated backend after Java migration

Aggregates all endpoint routers into a single router.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    nlp,
    ml,
    geoint,
    strategy,
    competitors,
    media,
    meta_ads,
    auth,
    keywords,
    dashboard,
)

# Create main API router
api_router = APIRouter()

# AI/ML Endpoints (Python handles these)
api_router.include_router(
    ai.router,
    tags=["AI"]
)

api_router.include_router(
    nlp.router,
    tags=["NLP"]
)

api_router.include_router(
    ml.router,
    tags=["ML"]
)

# GEOINT - Geographic Intelligence
api_router.include_router(
    geoint.router,
    prefix="/geoint",
    tags=["GEOINT"]
)

api_router.include_router(
    strategy.router,
    prefix="/strategies",
    tags=["Strategies"]
)

api_router.include_router(
    competitors.router,
    prefix="/competitors",
    tags=["Competitors"]
)

api_router.include_router(
    media.router,
    prefix="/media",
    tags=["Media & PR"]
)

api_router.include_router(
    meta_ads.router,
    prefix="/meta-ads",
    tags=["Meta Ads"]
)

# Authentication
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

# Keywords
api_router.include_router(
    keywords.router,
    prefix="/keywords",
    tags=["Keywords"]
)

# Dashboard
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"]
)
