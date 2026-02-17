"""
Competition Analyzer for GEOINT

Analyzes competitor presence and strength in specific regions for keywords.
Uses actual competitor data from database and Meta Ads insights.
"""
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging

from app.models.competitor import Competitor
from app.services.external.meta_ads import MetaAdsClient

logger = logging.getLogger(__name__)


class CompetitionAnalyzer:
    """
    Analyze competition levels for keywords in specific regions.

    Data sources:
    1. Database: Competitor records with region targeting
    2. Meta Ads API: Audience size and competition estimates
    3. Calculated: Competition density and strength metrics
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.meta_client = None  # Lazy initialization

    async def _get_meta_client(self) -> Optional[MetaAdsClient]:
        """Get or create Meta Ads client"""
        if self.meta_client is None:
            try:
                self.meta_client = MetaAdsClient()
            except Exception as e:
                logger.warning(f"Meta Ads client not available: {e}")
                return None
        return self.meta_client

    async def analyze_competition(
        self,
        keyword: str,
        region_name: str,
        region_id: str
    ) -> Dict:
        """
        Analyze competition for a keyword in a specific region

        Args:
            keyword: The keyword to analyze
            region_name: Name of the region (e.g., "İstanbul")
            region_id: UUID of the region

        Returns:
            Dict with competition metrics:
            {
                'competitor_count': int,
                'avg_competitor_strength': float (0-100),
                'competition_density': float (0-100),
                'market_saturation': float (0-100),
                'data_source': str,
                'real_data': bool
            }
        """
        # 1. Get competitors from database
        db_competitors = await self._get_competitors_from_db(keyword, region_name)

        # 2. Get Meta Ads insights if available
        meta_insights = await self._get_meta_insights(keyword, region_name)

        # 3. Calculate competition metrics
        competitor_count = len(db_competitors)

        if competitor_count > 0:
            # Calculate average strength from database competitors
            avg_strength = sum(c['strength'] for c in db_competitors) / competitor_count
        else:
            # Use Meta Ads estimate if available
            if meta_insights and meta_insights.get('competition_level'):
                # Convert Meta's competition level to 0-100 scale
                avg_strength = self._convert_meta_competition(meta_insights['competition_level'])
                competitor_count = meta_insights.get('estimated_competitors', 3)
            else:
                # Fallback to industry average
                avg_strength = 50.0
                competitor_count = 3

        # 4. Calculate competition density (competitors per 100k population)
        # This requires region population - we'll calculate it in the main task

        competition_data = {
            'competitor_count': competitor_count,
            'avg_competitor_strength': round(avg_strength, 2),
            'competition_density': self._calculate_density(competitor_count, meta_insights),
            'market_saturation': self._calculate_saturation(competitor_count, avg_strength),
            'data_source': 'database' if db_competitors else ('meta_ads' if meta_insights else 'estimated'),
            'real_data': len(db_competitors) > 0,
            'database_competitors': len(db_competitors),
            'meta_insights_available': meta_insights is not None
        }

        return competition_data

    async def _get_competitors_from_db(self, keyword: str, region_name: str) -> List[Dict]:
        """
        Get competitors from database that target this keyword/region

        Args:
            keyword: Keyword to search for
            region_name: Region name

        Returns:
            List of competitor dicts with strength scores
        """
        try:
            # Get all competitors from database
            result = await self.db.execute(
                select(Competitor)
            )
            all_competitors = result.scalars().all()

            matching_competitors = []

            for comp in all_competitors:
                # For now, include all competitors and calculate strength
                # In future, can add keyword/region filtering based on domain analysis

                # Calculate competitor strength (0-100)
                strength = self._calculate_competitor_strength(comp)

                matching_competitors.append({
                    'id': str(comp.id),
                    'name': comp.name or comp.domain,
                    'strength': strength,
                    'domain': comp.domain,
                    'category': comp.category
                })

            logger.info(f"Found {len(matching_competitors)} competitors in database")
            return matching_competitors

        except Exception as e:
            logger.error(f"Error fetching competitors from database: {e}")
            return []

    def _calculate_competitor_strength(self, competitor: Competitor) -> float:
        """
        Calculate competitor strength score (0-100) based on SEO metrics

        Factors:
        - Domain Authority (0-100)
        - Organic Traffic
        - Organic Keywords count
        - Backlinks count
        - Referring domains

        Args:
            competitor: Competitor model instance

        Returns:
            Strength score (0-100)
        """
        strength = 30.0  # Base strength

        # Domain Authority (0-40 points)
        if competitor.domain_authority:
            strength += (competitor.domain_authority / 100) * 40

        # Organic Traffic (0-15 points)
        if competitor.organic_traffic:
            # Normalize traffic (log scale)
            if competitor.organic_traffic > 100000:
                strength += 15
            elif competitor.organic_traffic > 10000:
                strength += 12
            elif competitor.organic_traffic > 1000:
                strength += 8
            else:
                strength += 5

        # Organic Keywords (0-10 points)
        if competitor.organic_keywords:
            if competitor.organic_keywords > 10000:
                strength += 10
            elif competitor.organic_keywords > 1000:
                strength += 7
            elif competitor.organic_keywords > 100:
                strength += 5
            else:
                strength += 3

        # Backlinks presence (0-5 points)
        if competitor.total_backlinks and competitor.total_backlinks > 1000:
            strength += 5

        return min(strength, 100.0)

    async def _get_meta_insights(self, keyword: str, region_name: str) -> Optional[Dict]:
        """
        Get Meta Ads insights for keyword in region

        Args:
            keyword: Keyword to analyze
            region_name: Region name

        Returns:
            Dict with Meta insights or None if unavailable
        """
        try:
            meta_client = await self._get_meta_client()
            if not meta_client:
                return None

            # Get audience insights
            audience = await meta_client.get_audience_insights(
                interests=[keyword],
                location='TR'
            )

            if audience:
                return {
                    'audience_size': audience.get('audience_size', 0),
                    'competition_level': self._estimate_competition_from_audience(
                        audience.get('audience_size', 0)
                    ),
                    'estimated_competitors': self._estimate_competitor_count(
                        audience.get('audience_size', 0)
                    )
                }

            return None

        except Exception as e:
            logger.warning(f"Could not fetch Meta Ads insights: {e}")
            return None

    def _estimate_competition_from_audience(self, audience_size: int) -> str:
        """
        Estimate competition level from audience size

        Args:
            audience_size: Total audience size from Meta

        Returns:
            'low', 'medium', or 'high'
        """
        if audience_size > 1_000_000:
            return 'high'
        elif audience_size > 100_000:
            return 'medium'
        else:
            return 'low'

    def _estimate_competitor_count(self, audience_size: int) -> int:
        """
        Estimate competitor count from audience size

        Assumes: Larger audiences = more competitors

        Args:
            audience_size: Total audience size

        Returns:
            Estimated number of competitors
        """
        if audience_size > 5_000_000:
            return 10
        elif audience_size > 1_000_000:
            return 7
        elif audience_size > 500_000:
            return 5
        elif audience_size > 100_000:
            return 3
        else:
            return 2

    def _convert_meta_competition(self, competition_level: str) -> float:
        """
        Convert Meta's competition level to 0-100 scale

        Args:
            competition_level: 'low', 'medium', or 'high'

        Returns:
            Strength score (0-100)
        """
        mapping = {
            'low': 35.0,
            'medium': 60.0,
            'high': 85.0
        }
        return mapping.get(competition_level, 50.0)

    def _calculate_density(self, competitor_count: int, meta_insights: Optional[Dict]) -> float:
        """
        Calculate competition density (0-100)

        Higher density = more competitors relative to market size

        Args:
            competitor_count: Number of competitors
            meta_insights: Meta Ads insights with audience size

        Returns:
            Density score (0-100)
        """
        if meta_insights and meta_insights.get('audience_size'):
            audience_size = meta_insights['audience_size']

            # Density = competitors per 100k audience members
            density = (competitor_count / max(audience_size / 100_000, 1)) * 100

            # Normalize to 0-100 scale (assume max 20 competitors per 100k)
            return min(density / 20 * 100, 100.0)

        # Without audience data, use simple competitor count mapping
        # 1-2 competitors = low (25)
        # 3-5 competitors = medium (50)
        # 6-10 competitors = high (75)
        # 10+ competitors = very high (90+)

        if competitor_count <= 2:
            return 25.0
        elif competitor_count <= 5:
            return 50.0
        elif competitor_count <= 10:
            return 75.0
        else:
            return min(90.0 + (competitor_count - 10) * 2, 100.0)

    def _calculate_saturation(self, competitor_count: int, avg_strength: float) -> float:
        """
        Calculate market saturation (0-100)

        Combines competitor count and average strength

        Args:
            competitor_count: Number of competitors
            avg_strength: Average competitor strength (0-100)

        Returns:
            Saturation score (0-100)
        """
        # Saturation = count factor + strength factor
        # More competitors + stronger competitors = higher saturation

        # Count factor (0-50): logarithmic scale
        if competitor_count == 0:
            count_factor = 0
        elif competitor_count == 1:
            count_factor = 15
        elif competitor_count <= 3:
            count_factor = 30
        elif competitor_count <= 5:
            count_factor = 40
        else:
            count_factor = min(45 + (competitor_count - 5) * 1, 50)

        # Strength factor (0-50): direct proportion
        strength_factor = (avg_strength / 100) * 50

        return min(count_factor + strength_factor, 100.0)

    async def get_competition_gap_score(
        self,
        keyword: str,
        region_name: str,
        region_id: str
    ) -> float:
        """
        Calculate competition gap score (0-100)

        Higher score = lower competition = more opportunity

        This is the inverse of market saturation

        Args:
            keyword: Keyword to analyze
            region_name: Region name
            region_id: Region UUID

        Returns:
            Competition gap score (0-100)
        """
        analysis = await self.analyze_competition(keyword, region_name, region_id)

        saturation = analysis['market_saturation']

        # Gap = 100 - saturation
        # But apply a floor to avoid 0 scores
        gap_score = max(100 - saturation, 15)

        return round(gap_score, 2)
