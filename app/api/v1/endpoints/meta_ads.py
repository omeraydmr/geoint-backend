"""
Meta Ads API Endpoints

Provides Facebook/Instagram advertising insights and recommendations.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from app.services.external.meta_ads import MetaAdsClient
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class AudienceInsightRequest(BaseModel):
    """Request model for audience insights"""
    interests: List[str]
    location: str = "TR"
    age_min: int = 18
    age_max: int = 65


class TargetingSuggestionRequest(BaseModel):
    """Request model for targeting suggestions"""
    keyword: str
    location: str = "TR"


class LocationInsightRequest(BaseModel):
    """Request model for location insights"""
    location_type: str = "city"  # city, region, country
    country: str = "TR"


# ============================================
# Endpoints
# ============================================

@router.post("/audience-insights")
async def get_audience_insights(
    request: AudienceInsightRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Get audience size and demographics for Meta Ads targeting

    **Example:**
    ```json
    {
        "interests": ["dijital pazarlama", "sosyal medya"],
        "location": "TR",
        "age_min": 25,
        "age_max": 45
    }
    ```

    **Returns:**
    - Estimated audience size
    - Reach potential
    - Currency and cost estimates
    """
    async with MetaAdsClient() as client:
        try:
            insights = await client.get_audience_insights(
                interests=request.interests,
                location=request.location,
                age_min=request.age_min,
                age_max=request.age_max
            )
            return {
                "success": True,
                "data": insights
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get audience insights: {str(e)}"
            )


@router.get("/ad-performance")
async def get_ad_performance(
    campaign_id: Optional[str] = None,
    date_preset: str = "last_30d",
    current_user: User = Depends(get_current_user)
):
    """
    Get Meta Ads campaign performance metrics

    **Parameters:**
    - `campaign_id`: Optional specific campaign ID
    - `date_preset`: Date range (last_7d, last_30d, last_90d, lifetime)

    **Returns:**
    - Campaign metrics (impressions, clicks, CTR, CPC, spend, conversions)
    - Total campaigns count
    """
    async with MetaAdsClient() as client:
        try:
            performance = await client.get_ad_performance(
                campaign_id=campaign_id,
                date_preset=date_preset
            )
            return {
                "success": True,
                "data": performance
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get ad performance: {str(e)}"
            )


@router.post("/targeting-suggestions")
async def get_targeting_suggestions(
    request: TargetingSuggestionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Get Meta Ads interest targeting suggestions based on keyword

    **Example:**
    ```json
    {
        "keyword": "kahve",
        "location": "TR"
    }
    ```

    **Returns:**
    - List of suggested interests with audience sizes
    - Interest categories and paths
    """
    async with MetaAdsClient() as client:
        try:
            suggestions = await client.get_targeting_suggestions(
                keyword=request.keyword,
                location=request.location
            )
            return {
                "success": True,
                "data": suggestions,
                "count": len(suggestions)
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get targeting suggestions: {str(e)}"
            )


@router.post("/location-insights")
async def get_location_insights(
    request: LocationInsightRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Get Meta Ads location targeting options

    **Example:**
    ```json
    {
        "location_type": "city",
        "country": "TR"
    }
    ```

    **Returns:**
    - List of targetable locations (cities, regions in Turkey)
    - Location keys for targeting
    """
    async with MetaAdsClient() as client:
        try:
            locations = await client.get_location_insights(
                location_type=request.location_type,
                country=request.country
            )
            return {
                "success": True,
                "data": locations,
                "count": len(locations)
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get location insights: {str(e)}"
            )


@router.get("/health")
async def meta_ads_health():
    """
    Health check for Meta Ads API integration

    **Returns:**
    - Service status
    - Configuration status
    """
    from app.core.config import settings

    has_config = bool(
        settings.META_ACCESS_TOKEN and
        settings.META_APP_ID and
        settings.META_APP_SECRET and
        settings.META_AD_ACCOUNT_ID
    )

    return {
        "success": True,
        "service": "Meta Ads API",
        "configured": has_config,
        "status": "operational" if has_config else "missing_configuration",
        "message": "All API keys configured" if has_config else "Missing META_ACCESS_TOKEN or META_AD_ACCOUNT_ID"
    }
