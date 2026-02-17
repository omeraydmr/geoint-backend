"""
Competitor Analysis Service

Aggregates data from multiple sources for comprehensive competitor intelligence.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from app.models.competitor import Competitor, CompetitorSnapshot, CompetitorBacklink
from app.services.external.dataforseo import DataForSEOClient
from app.services.ai.competitor_insights import CompetitorInsightsService
from app.schemas.competitor import (
    CompetitorTrendPoint,
    CompetitorTrendsResponse,
    BacklinkProfileResponse,
    BacklinkResponse,
    ContentGapResponse,
    ContentGapItem,
    AdIntelligenceResponse,
    TechStackResponse,
    MarketOverviewResponse,
    CompetitorComparisonResponse,
    CompetitorResponse,
)

logger = logging.getLogger(__name__)


class CompetitorAnalysisService:
    """
    Comprehensive competitor analysis service
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dataforseo = DataForSEOClient()
        self.ai_insights = CompetitorInsightsService()

    async def get_trends(
        self,
        competitor_id: UUID,
        time_range: str = "30d"
    ) -> CompetitorTrendsResponse:
        """
        Get historical trend data for a competitor

        Args:
            competitor_id: Competitor UUID
            time_range: Time range (7d, 30d, 90d, 1y)

        Returns:
            Trend data with growth rates
        """
        # Get competitor
        result = await self.db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise ValueError(f"Competitor {competitor_id} not found")

        # Calculate date range
        days_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        days = days_map.get(time_range, 30)
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get snapshots
        result = await self.db.execute(
            select(CompetitorSnapshot)
            .where(
                and_(
                    CompetitorSnapshot.competitor_id == competitor_id,
                    CompetitorSnapshot.snapshot_date >= start_date
                )
            )
            .order_by(CompetitorSnapshot.snapshot_date)
        )
        snapshots = result.scalars().all()

        # Convert to trend points
        data_points = [
            CompetitorTrendPoint(
                date=s.snapshot_date,
                domain_authority=s.domain_authority,
                organic_traffic=s.organic_traffic,
                organic_keywords=s.organic_keywords,
                total_backlinks=s.total_backlinks,
                referring_domains=s.referring_domains
            )
            for s in snapshots
        ]

        # Calculate growth rates
        growth_rates = self._calculate_growth_rates(data_points)

        return CompetitorTrendsResponse(
            competitor_id=competitor_id,
            domain=competitor.domain,
            time_range=time_range,
            data_points=data_points,
            growth_rates=growth_rates
        )

    async def get_backlink_profile(
        self,
        competitor_id: UUID,
        limit: int = 100
    ) -> BacklinkProfileResponse:
        """
        Get detailed backlink profile for a competitor

        Args:
            competitor_id: Competitor UUID
            limit: Number of backlinks to return

        Returns:
            Backlink profile with analysis
        """
        # Get competitor
        result = await self.db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise ValueError(f"Competitor {competitor_id} not found")

        # Try to get fresh backlink data from DataForSEO
        backlinks_data = await self._fetch_backlinks_from_api(competitor.domain, limit)

        # Get stored backlinks as fallback
        result = await self.db.execute(
            select(CompetitorBacklink)
            .where(CompetitorBacklink.competitor_id == competitor_id)
            .order_by(desc(CompetitorBacklink.domain_authority))
            .limit(limit)
        )
        stored_backlinks = result.scalars().all()

        # Use API data if available, otherwise use stored
        backlinks = backlinks_data if backlinks_data else [
            BacklinkResponse(
                id=b.id,
                source_url=b.source_url,
                source_domain=b.source_domain,
                target_url=b.target_url,
                anchor_text=b.anchor_text,
                domain_authority=b.domain_authority,
                page_authority=b.page_authority,
                link_type=b.link_type,
                first_seen=b.first_seen,
                last_seen=b.last_seen
            )
            for b in stored_backlinks
        ]

        # Calculate stats
        dofollow = sum(1 for b in backlinks if b.link_type == "dofollow")
        nofollow = len(backlinks) - dofollow

        # Calculate anchor text distribution
        anchor_counts = {}
        for b in backlinks:
            anchor = b.anchor_text or "(no anchor)"
            anchor_counts[anchor] = anchor_counts.get(anchor, 0) + 1

        top_anchors = sorted(
            [{"anchor": k, "count": v, "percentage": round(v / len(backlinks) * 100, 1)}
             for k, v in anchor_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        # Calculate referring domain stats
        domain_counts = {}
        domain_da = {}
        for b in backlinks:
            domain_counts[b.source_domain] = domain_counts.get(b.source_domain, 0) + 1
            domain_da[b.source_domain] = b.domain_authority or 0

        top_domains = sorted(
            [{"domain": k, "backlinks": v, "da": domain_da.get(k, 0)}
             for k, v in domain_counts.items()],
            key=lambda x: x["da"],
            reverse=True
        )[:10]

        return BacklinkProfileResponse(
            competitor_id=competitor_id,
            domain=competitor.domain,
            total_backlinks=competitor.total_backlinks or len(backlinks),
            referring_domains=competitor.referring_domains or len(domain_counts),
            dofollow_count=dofollow,
            nofollow_count=nofollow,
            top_anchor_texts=top_anchors,
            top_referring_domains=top_domains,
            backlinks=backlinks,
            new_backlinks_30d=0,  # Would need historical data
            lost_backlinks_30d=0
        )

    async def get_content_gaps(
        self,
        competitor_id: UUID,
        user_domain: Optional[str] = None
    ) -> ContentGapResponse:
        """
        Identify content gap opportunities

        Args:
            competitor_id: Competitor UUID
            user_domain: User's domain for comparison

        Returns:
            Content gap analysis
        """
        # Get competitor
        result = await self.db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise ValueError(f"Competitor {competitor_id} not found")

        # Get competitor keywords
        competitor_keywords = await self.dataforseo.get_competitor_keywords(
            competitor.domain,
            limit=500
        )

        # Get user keywords if domain provided
        user_keywords = []
        if user_domain:
            user_keywords = await self.dataforseo.get_competitor_keywords(
                user_domain,
                limit=500
            )

        # Use AI to identify content gaps
        content_categories = await self.ai_insights.identify_content_gaps(
            competitor_keywords,
            user_keywords
        )

        # Get top performing pages from latest snapshot
        result = await self.db.execute(
            select(CompetitorSnapshot)
            .where(CompetitorSnapshot.competitor_id == competitor_id)
            .order_by(desc(CompetitorSnapshot.snapshot_date))
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()

        top_pages = []
        if snapshot and snapshot.top_keywords:
            # Group keywords by URL
            url_stats = {}
            for kw in snapshot.top_keywords:
                url = kw.get("url", "")
                if url not in url_stats:
                    url_stats[url] = {"url": url, "traffic": 0, "keywords": 0}
                url_stats[url]["traffic"] += kw.get("search_volume", 0) // (kw.get("position", 10) + 1)
                url_stats[url]["keywords"] += 1

            top_pages = sorted(url_stats.values(), key=lambda x: x["traffic"], reverse=True)[:10]

        # Convert to content gap items
        content_gaps = []
        for cat in content_categories:
            for kw in cat.get("keywords", [])[:5]:
                # Find volume from competitor keywords
                kw_data = next((k for k in competitor_keywords if k.get("keyword") == kw), {})
                content_gaps.append(ContentGapItem(
                    topic=kw,
                    search_volume=kw_data.get("search_volume", 0),
                    difficulty=kw_data.get("keyword_difficulty"),
                    competitor_url=kw_data.get("url"),
                    content_type=cat.get("content_type", "blog"),
                    opportunity_score=0.8 if cat.get("priority") == "high" else 0.5
                ))

        return ContentGapResponse(
            competitor_id=competitor_id,
            domain=competitor.domain,
            total_gaps=len(content_gaps),
            content_gaps=content_gaps[:20],
            top_performing_pages=top_pages
        )

    async def get_ad_intelligence(
        self,
        competitor_id: UUID
    ) -> AdIntelligenceResponse:
        """
        Get advertising intelligence for a competitor

        Args:
            competitor_id: Competitor UUID

        Returns:
            Ad intelligence data
        """
        # Get competitor
        result = await self.db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise ValueError(f"Competitor {competitor_id} not found")

        # Get paid keyword data from DataForSEO
        # Note: This would use the Ads API in production
        paid_keywords = []
        try:
            # This would be a separate API call for paid keyword data
            # For now, estimate based on paid_keywords count
            pass
        except Exception as e:
            logger.warning(f"Could not fetch ad data: {e}")

        # Estimate ad spend based on available metrics
        estimated_spend = None
        if competitor.paid_keywords and competitor.paid_keywords > 0:
            # Rough estimate: avg CPC * keywords * estimated clicks
            avg_cpc = 0.5  # USD
            estimated_clicks = competitor.paid_keywords * 50  # Rough estimate
            estimated_spend = int(avg_cpc * estimated_clicks)

        return AdIntelligenceResponse(
            competitor_id=competitor_id,
            domain=competitor.domain,
            estimated_monthly_spend=competitor.estimated_ad_spend or estimated_spend,
            estimated_ad_keywords=competitor.estimated_ad_keywords or competitor.paid_keywords or 0,
            top_ad_keywords=paid_keywords[:20],
            ad_copy_samples=[],  # Would require scraping
            display_ads_detected=0,
            search_ads_detected=competitor.paid_keywords or 0
        )

    async def get_tech_stack(
        self,
        competitor_id: UUID
    ) -> TechStackResponse:
        """
        Detect technology stack for a competitor

        Args:
            competitor_id: Competitor UUID

        Returns:
            Technology stack information
        """
        # Get competitor
        result = await self.db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise ValueError(f"Competitor {competitor_id} not found")

        # Use stored technologies or fetch new
        technologies = competitor.technologies or {}

        # Default structure
        return TechStackResponse(
            competitor_id=competitor_id,
            domain=competitor.domain,
            categories=technologies.get("categories", {}),
            cms=technologies.get("cms"),
            ecommerce=technologies.get("ecommerce"),
            analytics=technologies.get("analytics", []),
            advertising=technologies.get("advertising", []),
            hosting=technologies.get("hosting"),
            cdn=technologies.get("cdn"),
            frameworks=technologies.get("frameworks", []),
            detected_at=competitor.last_analyzed_at or datetime.utcnow()
        )

    async def compare_competitors(
        self,
        competitor_ids: List[UUID],
        user_domain: Optional[str] = None
    ) -> CompetitorComparisonResponse:
        """
        Compare multiple competitors side-by-side

        Args:
            competitor_ids: List of competitor UUIDs (2-4)
            user_domain: Optional user's domain for comparison

        Returns:
            Comparison data
        """
        # Get competitors
        result = await self.db.execute(
            select(Competitor).where(Competitor.id.in_(competitor_ids))
        )
        competitors = result.scalars().all()

        if len(competitors) < 2:
            raise ValueError("Need at least 2 competitors to compare")

        # Convert to response models
        competitor_responses = [
            CompetitorResponse.model_validate(c) for c in competitors
        ]

        # Build metrics comparison
        metrics = ["domain_authority", "organic_traffic", "organic_keywords",
                   "total_backlinks", "referring_domains"]

        metrics_comparison = {}
        for metric in metrics:
            metrics_comparison[metric] = {
                c.domain: getattr(c, metric, 0) or 0
                for c in competitors
            }

        # Calculate rankings for each metric
        rankings = {}
        for metric in metrics:
            sorted_domains = sorted(
                [(c.domain, getattr(c, metric, 0) or 0) for c in competitors],
                key=lambda x: x[1],
                reverse=True
            )
            rankings[metric] = [d[0] for d in sorted_domains]

        # Build radar chart data (normalized 0-100)
        radar_data = []
        for c in competitors:
            data_point = {"domain": c.domain}
            for metric in metrics:
                value = getattr(c, metric, 0) or 0
                max_val = max(getattr(comp, metric, 0) or 0 for comp in competitors)
                normalized = (value / max_val * 100) if max_val > 0 else 0
                data_point[metric] = round(normalized, 1)
            radar_data.append(data_point)

        return CompetitorComparisonResponse(
            user_domain=user_domain,
            competitors=competitor_responses,
            metrics_comparison=metrics_comparison,
            rankings=rankings,
            radar_data=radar_data
        )

    async def get_market_overview(
        self,
        user_id: UUID,
        user_domain: Optional[str] = None
    ) -> MarketOverviewResponse:
        """
        Get market overview with industry benchmarks

        Args:
            user_id: User's UUID
            user_domain: User's domain

        Returns:
            Market overview data
        """
        # Get all competitors for user
        result = await self.db.execute(
            select(Competitor).where(Competitor.user_id == user_id)
        )
        competitors = result.scalars().all()

        if not competitors:
            return MarketOverviewResponse(
                total_competitors=0,
                industry_benchmarks={},
                market_leaders=[],
                your_position={},
                growth_opportunities=["Add competitors to start tracking your market"]
            )

        # Calculate benchmarks
        metrics = ["domain_authority", "organic_traffic", "organic_keywords",
                   "total_backlinks", "referring_domains"]

        benchmarks = {}
        for metric in metrics:
            values = [getattr(c, metric, 0) or 0 for c in competitors]
            benchmarks[metric] = {
                "avg": round(sum(values) / len(values), 1) if values else 0,
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "your_value": None  # Would need user's domain metrics
            }

        # Find market leaders
        leaders = []
        for metric in metrics:
            sorted_comps = sorted(
                competitors,
                key=lambda c: getattr(c, metric, 0) or 0,
                reverse=True
            )
            if sorted_comps:
                leader = sorted_comps[0]
                leaders.append({
                    "domain": leader.domain,
                    "metric": metric,
                    "value": getattr(leader, metric, 0) or 0
                })

        # Identify opportunities
        opportunities = []
        avg_da = benchmarks.get("domain_authority", {}).get("avg", 0)
        if avg_da < 50:
            opportunities.append("Build domain authority through quality content and backlinks")
        if benchmarks.get("organic_keywords", {}).get("avg", 0) < 1000:
            opportunities.append("Expand keyword coverage with comprehensive content")
        if benchmarks.get("total_backlinks", {}).get("avg", 0) < 1000:
            opportunities.append("Focus on link building to match competitor profiles")

        return MarketOverviewResponse(
            total_competitors=len(competitors),
            industry_benchmarks=benchmarks,
            market_leaders=leaders[:5],
            your_position={},  # Would calculate if user_domain provided
            growth_opportunities=opportunities or ["Continue monitoring competitor movements"]
        )

    async def generate_ai_insights(
        self,
        competitor_id: UUID,
        regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate AI-powered SWOT analysis and recommendations

        Args:
            competitor_id: Competitor UUID
            regenerate: Force regeneration even if cached

        Returns:
            AI insights including SWOT and recommendations
        """
        # Get competitor
        result = await self.db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise ValueError(f"Competitor {competitor_id} not found")

        # Check cache if not regenerating
        if not regenerate and competitor.ai_insights:
            cached = competitor.ai_insights
            # Check if still fresh (7 days)
            if cached.get("generated_at"):
                generated = datetime.fromisoformat(cached["generated_at"])
                if datetime.utcnow() - generated < timedelta(days=7):
                    return cached

        # Build competitor data dict
        competitor_data = {
            "domain": competitor.domain,
            "domain_authority": competitor.domain_authority,
            "organic_traffic": competitor.organic_traffic,
            "organic_keywords": competitor.organic_keywords,
            "total_backlinks": competitor.total_backlinks,
            "referring_domains": competitor.referring_domains,
            "paid_keywords": competitor.paid_keywords,
        }

        # Generate SWOT analysis
        swot = await self.ai_insights.generate_swot_analysis(competitor_data)

        # Generate recommendations
        recommendations = await self.ai_insights.generate_recommendations(competitor_data)
        swot["recommendations"] = recommendations

        # Serialize datetime for storage
        swot["generated_at"] = swot["generated_at"].isoformat()

        # Cache the insights
        competitor.ai_insights = swot
        competitor.updated_at = datetime.utcnow()
        await self.db.commit()

        return swot

    async def _fetch_backlinks_from_api(
        self,
        domain: str,
        limit: int
    ) -> List[BacklinkResponse]:
        """Fetch backlinks from DataForSEO API"""
        # This would call the DataForSEO backlinks API
        # For now, return empty list as it requires additional API setup
        return []

    def _calculate_growth_rates(
        self,
        data_points: List[CompetitorTrendPoint]
    ) -> Dict[str, float]:
        """Calculate growth rates from trend data"""
        if len(data_points) < 2:
            return {}

        first = data_points[0]
        last = data_points[-1]

        metrics = ["domain_authority", "organic_traffic", "organic_keywords",
                   "total_backlinks", "referring_domains"]

        growth_rates = {}
        for metric in metrics:
            first_val = getattr(first, metric, 0) or 0
            last_val = getattr(last, metric, 0) or 0

            if first_val > 0:
                growth = ((last_val - first_val) / first_val) * 100
                growth_rates[metric] = round(growth, 2)
            else:
                growth_rates[metric] = 0.0

        return growth_rates

    async def close(self):
        """Close service connections"""
        await self.dataforseo.close()
