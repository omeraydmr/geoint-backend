"""
GEOINT Score Calculator

Calculates geographic intelligence scores for keywords across Turkish regions.

Formula:
Score = (0.4 × Search_Index) + (0.25 × Trend_Score) +
        (0.20 × Demo_Fit) + (0.15 × Competition_Gap)
"""
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import numpy as np
from datetime import datetime

from app.models.geo import GEOINTScore, RegionType
from app.core.config import settings


class GEOINTCalculator:
    """
    GEOINT Score Calculator

    Combines multiple data sources to calculate geographic opportunity scores:
    - Search demand (Google Trends, search volume)
    - Trend momentum (YoY, MoM changes)
    - Demographic fit (population, income levels)
    - Competition gap (competitor presence)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.weights = {
            'search': 0.40,
            'trend': 0.25,
            'demo': 0.20,
            'competition': 0.15
        }

    async def calculate_score(
        self,
        keyword_id: str,
        region_id: str,
        region_type: RegionType,
        search_index: float,
        trend_data: Dict,
        demographic_data: Dict,
        competition_data: Dict,
        region_name: Optional[str] = None
    ) -> GEOINTScore:
        """
        Calculate GEOINT score for a keyword in a specific region

        Args:
            keyword_id: UUID of the keyword
            region_id: UUID of the region (province/district/neighborhood)
            region_type: Type of region (PROVINCE, DISTRICT, NEIGHBORHOOD)
            search_index: Raw search volume index (0-100 from Google Trends)
            trend_data: Trend metrics {yoy_change: float, mom_change: float, ...}
            demographic_data: Demographics {population: int, income_index: float, ...}
            competition_data: Competition metrics {competitor_count: int, avg_strength: float}

        Returns:
            GEOINTScore object with calculated scores
        """

        # Normalize search index (0-100)
        normalized_search = min(max(search_index, 0), 100)

        # Calculate component scores
        trend_score = self._calculate_trend_score(trend_data)
        demo_fit = self._calculate_demographic_fit(demographic_data)
        competition_gap = self._calculate_competition_gap(competition_data)

        # Calculate composite GEOINT score (weighted average)
        geoint_score = (
            self.weights['search'] * normalized_search +
            self.weights['trend'] * trend_score +
            self.weights['demo'] * demo_fit +
            self.weights['competition'] * competition_gap
        )

        # Create score record
        raw_data_dict = {
            'trend_data': trend_data,
            'demographic_data': demographic_data,
            'competition_data': competition_data
        }

        # Add region name if provided
        if region_name:
            raw_data_dict['region_name'] = region_name

        score = GEOINTScore(
            keyword_id=keyword_id,
            region_type=region_type,
            region_id=region_id,
            search_index=normalized_search,
            trend_score=trend_score,
            demographic_fit=demo_fit,
            competition_gap=competition_gap,
            geoint_score=round(geoint_score, 2),
            trend_direction=self._get_trend_direction(trend_data),
            trend_change_pct=trend_data.get('mom_change', 0),
            raw_data=raw_data_dict,
            calculated_at=datetime.utcnow()
        )

        return score

    def _calculate_trend_score(self, trend_data: Dict) -> float:
        """
        Calculate trend momentum score (0-100)

        Higher scores for growing trends.
        Combines YoY and MoM changes.
        """
        yoy = trend_data.get('yoy_change', 0)  # Year-over-year %
        mom = trend_data.get('mom_change', 0)  # Month-over-month %

        # Weight: 50% YoY (long-term), 50% MoM (short-term)
        raw_score = (0.5 * yoy) + (0.5 * mom)

        # Convert to 0-100 scale (center at 50 for no change)
        # -100% change = 0, 0% change = 50, +100% change = 100
        normalized_score = 50 + (raw_score / 2)

        return min(max(normalized_score, 0), 100)

    def _calculate_demographic_fit(self, demo_data: Dict) -> float:
        """
        Calculate demographic fit score (0-100)

        Considers:
        - Population size (larger = more opportunity)
        - Income levels (higher = more purchasing power)
        """
        population = demo_data.get('population', 0)
        income_index = demo_data.get('income_index', 50)  # 0-100 scale

        # Normalize population (logarithmic scale)
        # 1,000 pop = 0, 100,000 pop = 50, 10M pop = 100
        pop_score = self._normalize_population(population)

        # Combine: 50% population, 50% income
        return (0.5 * pop_score) + (0.5 * income_index)

    def _calculate_competition_gap(self, comp_data: Dict) -> float:
        """
        Calculate competition gap score (0-100)

        Lower competition = higher score (more opportunity)
        """
        competitor_count = comp_data.get('competitor_count', 0)
        avg_strength = comp_data.get('avg_competitor_strength', 50)  # 0-100

        # Penalize for number of competitors (max penalty at 5+ competitors)
        count_penalty = min(competitor_count * 10, 50)

        # Penalize for competitor strength
        strength_penalty = avg_strength / 2

        # Higher score = less competition
        return 100 - (count_penalty + strength_penalty)

    def _normalize_population(self, population: int) -> float:
        """
        Normalize population to 0-100 scale using logarithmic transformation

        This handles the wide range of population sizes (1K to 15M in Turkey)
        """
        if population <= 0:
            return 0

        # Use log10 scale: 10^3 = 0, 10^5 = 50, 10^7 = 100
        log_pop = np.log10(population)

        # Map to 0-100 scale
        # log10(1000) = 3 -> 0
        # log10(100000) = 5 -> 50
        # log10(10000000) = 7 -> 100
        normalized = ((log_pop - 3) / 4) * 100

        return min(max(normalized, 0), 100)

    def _get_trend_direction(self, trend_data: Dict) -> str:
        """
        Get simplified trend direction based on MoM change

        Returns: 'up', 'down', or 'stable'
        """
        mom = trend_data.get('mom_change', 0)

        if mom > 10:
            return 'up'
        elif mom < -10:
            return 'down'
        else:
            return 'stable'

    async def calculate_bulk_scores(
        self,
        keyword_id: str,
        region_scores: List[Dict]
    ) -> List[GEOINTScore]:
        """
        Calculate GEOINT scores for multiple regions in bulk

        Args:
            keyword_id: UUID of the keyword
            region_scores: List of dicts with region data

        Returns:
            List of GEOINTScore objects
        """
        scores = []

        for region_data in region_scores:
            score = await self.calculate_score(
                keyword_id=keyword_id,
                region_id=region_data['region_id'],
                region_type=region_data['region_type'],
                search_index=region_data['search_index'],
                trend_data=region_data.get('trend_data', {}),
                demographic_data=region_data.get('demographic_data', {}),
                competition_data=region_data.get('competition_data', {})
            )
            scores.append(score)

        return scores

    async def get_top_regions(
        self,
        keyword_id: str,
        region_type: Optional[RegionType] = None,
        limit: int = 10
    ) -> List[GEOINTScore]:
        """
        Get top-scoring regions for a keyword

        Args:
            keyword_id: UUID of the keyword
            region_type: Filter by region type (optional)
            limit: Number of top regions to return

        Returns:
            List of top GEOINTScore objects
        """
        query = select(GEOINTScore).where(GEOINTScore.keyword_id == keyword_id)

        if region_type:
            query = query.where(GEOINTScore.region_type == region_type)

        query = query.order_by(GEOINTScore.geoint_score.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())
