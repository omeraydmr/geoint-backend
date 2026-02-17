"""
Meta (Facebook) Ads API Integration

Provides Facebook/Instagram ad insights and targeting recommendations.

API Documentation: https://developers.facebook.com/docs/marketing-apis
"""
from typing import List, Dict, Optional
import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class MetaAdsClient:
    """
    Meta Marketing API Client

    Requires:
    - META_ACCESS_TOKEN: Long-lived user or system user access token
    - META_APP_ID: Your Facebook App ID
    - META_APP_SECRET: Your Facebook App Secret
    - META_AD_ACCOUNT_ID: Your Ad Account ID (format: act_XXXXXXXX)

    Get credentials from: https://developers.facebook.com/apps/
    """

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(self):
        self.access_token = settings.META_ACCESS_TOKEN
        self.ad_account_id = settings.META_AD_ACCOUNT_ID
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def get_audience_insights(
        self,
        interests: List[str],
        location: str = "TR",  # Turkey
        age_min: int = 18,
        age_max: int = 65
    ) -> Dict:
        """
        Get audience size and demographics for targeting

        Args:
            interests: List of interest keywords
            location: Country code
            age_min: Minimum age
            age_max: Maximum age

        Returns:
            Audience insights including size and demographics
        """
        if not self.access_token:
            return self._fallback_audience_data()

        try:
            url = f"{self.BASE_URL}/{self.ad_account_id}/reachestimate"

            params = {
                "access_token": self.access_token,
                "targeting_spec": {
                    "geo_locations": {"countries": [location]},
                    "age_min": age_min,
                    "age_max": age_max,
                    "interests": [{"name": interest} for interest in interests],
                },
                "currency": "TRY",
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            return {
                "audience_size": data.get("users", 0),
                "reach_estimate": data.get("estimate_ready", False),
                "currency": "TRY",
                "interests": interests,
            }

        except Exception as e:
            logger.error(f"❌ Error getting audience insights: {e}")
            return self._fallback_audience_data()

    async def get_ad_performance(
        self,
        campaign_id: Optional[str] = None,
        date_preset: str = "last_30d"
    ) -> Dict:
        """
        Get ad campaign performance metrics

        Args:
            campaign_id: Specific campaign ID (optional)
            date_preset: Date range (last_7d, last_30d, lifetime, etc.)

        Returns:
            Performance metrics
        """
        if not self.access_token:
            return self._fallback_performance_data()

        try:
            # If specific campaign, query it; otherwise query all campaigns
            endpoint = f"{self.ad_account_id}/campaigns" if not campaign_id else campaign_id

            url = f"{self.BASE_URL}/{endpoint}/insights"

            params = {
                "access_token": self.access_token,
                "date_preset": date_preset,
                "fields": "campaign_name,impressions,clicks,ctr,cpc,spend,conversions,conversion_rate",
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            campaigns = data.get("data", [])

            results = []
            for campaign in campaigns:
                results.append({
                    "campaign_name": campaign.get("campaign_name"),
                    "impressions": int(campaign.get("impressions", 0)),
                    "clicks": int(campaign.get("clicks", 0)),
                    "ctr": float(campaign.get("ctr", 0)),
                    "avg_cpc": float(campaign.get("cpc", 0)),
                    "cost": float(campaign.get("spend", 0)),
                    "conversions": int(campaign.get("conversions", 0)),
                    "conversion_rate": float(campaign.get("conversion_rate", 0)),
                })

            return {
                "campaigns": results,
                "total_campaigns": len(results),
                "currency": "TRY",
            }

        except Exception as e:
            logger.error(f"❌ Error getting Meta ad performance: {e}")
            return self._fallback_performance_data()

    async def get_targeting_suggestions(
        self,
        keyword: str,
        location: str = "TR"
    ) -> List[Dict]:
        """
        Get interest targeting suggestions based on keyword

        Args:
            keyword: Seed keyword
            location: Country code

        Returns:
            List of suggested interests for targeting
        """
        if not self.access_token:
            return []

        try:
            url = f"{self.BASE_URL}/search"

            params = {
                "access_token": self.access_token,
                "type": "adinterest",
                "q": keyword,
                "locale": "tr_TR",
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            interests = data.get("data", [])

            return [
                {
                    "id": interest.get("id"),
                    "name": interest.get("name"),
                    "audience_size": interest.get("audience_size", 0),
                    "path": interest.get("path", []),
                }
                for interest in interests
            ]

        except Exception as e:
            logger.error(f"❌ Error getting targeting suggestions: {e}")
            return []

    async def get_location_insights(
        self,
        location_type: str = "city",
        country: str = "TR"
    ) -> List[Dict]:
        """
        Get location targeting options (cities, regions in Turkey)

        Args:
            location_type: city, region, country
            country: Country code

        Returns:
            List of targetable locations
        """
        if not self.access_token:
            return []

        try:
            url = f"{self.BASE_URL}/search"

            params = {
                "access_token": self.access_token,
                "type": "adgeolocation",
                "location_types": [location_type],
                "q": country,
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            locations = data.get("data", [])

            return [
                {
                    "key": loc.get("key"),
                    "name": loc.get("name"),
                    "type": loc.get("type"),
                    "country_code": loc.get("country_code"),
                }
                for loc in locations
            ]

        except Exception as e:
            logger.error(f"❌ Error getting location insights: {e}")
            return []

    def _fallback_audience_data(self) -> Dict:
        """Fallback audience data"""
        logger.warning("⚠️ Using fallback audience data")
        return {
            "audience_size": 1000000,  # Placeholder
            "reach_estimate": False,
            "currency": "TRY",
            "interests": [],
        }

    def _fallback_performance_data(self) -> Dict:
        """Fallback performance data"""
        logger.warning("⚠️ Using fallback performance data")
        return {
            "campaigns": [],
            "total_campaigns": 0,
            "currency": "TRY",
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
