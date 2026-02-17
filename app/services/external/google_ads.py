"""
Google Ads API Integration

Provides keyword metrics, ad performance data, and campaign recommendations
for the Turkish market.

API Documentation: https://developers.google.com/google-ads/api/docs/start
"""
from typing import List, Dict, Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleAdsClient:
    """
    Google Ads API Client

    Requires:
    - GOOGLE_ADS_DEVELOPER_TOKEN
    - GOOGLE_ADS_CLIENT_ID
    - GOOGLE_ADS_CLIENT_SECRET
    - GOOGLE_ADS_REFRESH_TOKEN
    - GOOGLE_ADS_CUSTOMER_ID

    Get credentials from: https://ads.google.com/aw/apicenter
    """

    def __init__(self):
        self.developer_token = settings.GOOGLE_ADS_DEVELOPER_TOKEN
        self.client_id = settings.GOOGLE_ADS_CLIENT_ID
        self.client_secret = settings.GOOGLE_ADS_CLIENT_SECRET
        self.refresh_token = settings.GOOGLE_ADS_REFRESH_TOKEN
        self.customer_id = settings.GOOGLE_ADS_CUSTOMER_ID
        self._client = None

    def _get_client(self):
        """
        Initialize Google Ads API client

        Install: pip install google-ads
        """
        if self._client is None:
            try:
                from google.ads.googleads.client import GoogleAdsClient as GAClient

                credentials = {
                    "developer_token": self.developer_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "use_proto_plus": True,
                }

                self._client = GAClient.load_from_dict(credentials)
                logger.info("✅ Google Ads client initialized")
            except ImportError:
                logger.warning("⚠️ google-ads library not installed")
                self._client = None
            except Exception as e:
                logger.error(f"❌ Failed to initialize Google Ads client: {e}")
                self._client = None

        return self._client

    async def get_keyword_ideas(
        self,
        keywords: List[str],
        location_id: str = "2792",  # Turkey
        language_id: str = "1019"  # Turkish
    ) -> List[Dict]:
        """
        Get keyword ideas and search volume data

        Args:
            keywords: Seed keywords
            location_id: Geographic location (2792 = Turkey)
            language_id: Language (1019 = Turkish)

        Returns:
            List of keyword ideas with metrics
        """
        client = self._get_client()
        if not client:
            return self._fallback_keyword_data(keywords)

        try:
            keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")

            request = client.get_type("GenerateKeywordIdeasRequest")
            request.customer_id = self.customer_id
            request.language = client.get_service("GoogleAdsService").language_constant_path(language_id)
            request.geo_target_constants.append(
                client.get_service("GoogleAdsService").geo_target_constant_path(location_id)
            )

            # Set keyword seeds
            request.keyword_seed.keywords.extend(keywords)

            # Get ideas
            response = keyword_plan_idea_service.generate_keyword_ideas(request=request)

            results = []
            for idea in response.results:
                keyword_text = idea.text
                metrics = idea.keyword_idea_metrics

                results.append({
                    "keyword": keyword_text,
                    "search_volume": metrics.avg_monthly_searches,
                    "competition": metrics.competition.name,  # LOW, MEDIUM, HIGH
                    "cpc_low": self._micros_to_tl(metrics.low_top_of_page_bid_micros),
                    "cpc_high": self._micros_to_tl(metrics.high_top_of_page_bid_micros),
                    "cpc_avg": (
                        self._micros_to_tl(metrics.low_top_of_page_bid_micros) +
                        self._micros_to_tl(metrics.high_top_of_page_bid_micros)
                    ) / 2,
                })

            logger.info(f"📊 Got {len(results)} keyword ideas from Google Ads")
            return results

        except Exception as e:
            logger.error(f"❌ Error getting keyword ideas: {e}")
            return self._fallback_keyword_data(keywords)

    async def get_ad_performance(
        self,
        campaign_id: Optional[str] = None,
        date_range: str = "LAST_30_DAYS"
    ) -> Dict:
        """
        Get ad campaign performance metrics

        Args:
            campaign_id: Specific campaign ID (optional)
            date_range: Date range (LAST_7_DAYS, LAST_30_DAYS, etc.)

        Returns:
            Performance metrics
        """
        client = self._get_client()
        if not client:
            return self._fallback_performance_data()

        try:
            ga_service = client.get_service("GoogleAdsService")

            query = """
                SELECT
                    campaign.id,
                    campaign.name,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversion_rate
                FROM campaign
                WHERE segments.date DURING {}
            """.format(date_range)

            if campaign_id:
                query += f" AND campaign.id = {campaign_id}"

            response = ga_service.search_stream(
                customer_id=self.customer_id,
                query=query
            )

            results = []
            for batch in response:
                for row in batch.results:
                    campaign = row.campaign
                    metrics = row.metrics

                    results.append({
                        "campaign_id": campaign.id,
                        "campaign_name": campaign.name,
                        "impressions": metrics.impressions,
                        "clicks": metrics.clicks,
                        "ctr": metrics.ctr,
                        "avg_cpc": self._micros_to_tl(metrics.average_cpc),
                        "cost": self._micros_to_tl(metrics.cost_micros),
                        "conversions": metrics.conversions,
                        "conversion_rate": metrics.conversion_rate,
                    })

            return {
                "campaigns": results,
                "total_campaigns": len(results)
            }

        except Exception as e:
            logger.error(f"❌ Error getting ad performance: {e}")
            return self._fallback_performance_data()

    async def get_location_performance(
        self,
        campaign_id: str,
        date_range: str = "LAST_30_DAYS"
    ) -> List[Dict]:
        """
        Get performance by geographic location

        Useful for analyzing which Turkish regions are performing best.
        """
        client = self._get_client()
        if not client:
            return []

        try:
            ga_service = client.get_service("GoogleAdsService")

            query = """
                SELECT
                    user_location_view.country_criterion_id,
                    user_location_view.targeting_location,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.ctr,
                    metrics.conversions
                FROM user_location_view
                WHERE campaign.id = {}
                AND segments.date DURING {}
            """.format(campaign_id, date_range)

            response = ga_service.search_stream(
                customer_id=self.customer_id,
                query=query
            )

            results = []
            for batch in response:
                for row in batch.results:
                    location = row.user_location_view
                    metrics = row.metrics

                    results.append({
                        "location_id": location.country_criterion_id,
                        "location_name": location.targeting_location,
                        "impressions": metrics.impressions,
                        "clicks": metrics.clicks,
                        "ctr": metrics.ctr,
                        "conversions": metrics.conversions,
                    })

            return results

        except Exception as e:
            logger.error(f"❌ Error getting location performance: {e}")
            return []

    def _micros_to_tl(self, micros: int) -> float:
        """Convert micros to Turkish Lira"""
        return micros / 1_000_000 if micros else 0.0

    def _fallback_keyword_data(self, keywords: List[str]) -> List[Dict]:
        """Fallback data when API is unavailable"""
        logger.warning("⚠️ Using fallback keyword data")
        return [
            {
                "keyword": kw,
                "search_volume": 1000,  # Placeholder
                "competition": "MEDIUM",
                "cpc_low": 0.50,
                "cpc_high": 2.00,
                "cpc_avg": 1.25,
            }
            for kw in keywords
        ]

    def _fallback_performance_data(self) -> Dict:
        """Fallback performance data"""
        logger.warning("⚠️ Using fallback performance data")
        return {
            "campaigns": [],
            "total_campaigns": 0
        }
