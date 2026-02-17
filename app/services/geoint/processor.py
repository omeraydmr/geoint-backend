import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.keyword import Keyword
from app.models.geo import Province, District, GEOINTScore, RegionType
from app.services.trends.google_trends import GoogleTrendsCollector
from app.services.geoint.calculator import GEOINTCalculator
from app.services.geoint.economic_data import EconomicDataService
from app.services.geoint.competition_analyzer import CompetitionAnalyzer
from app.core.cache import cache_invalidate

logger = logging.getLogger(__name__)

class GEOINTProcessor:
    """
    Orchestrates the GEOINT scoring process:
    1. Collects data (Trends, Economics, Competition)
    2. Calculates scores for Provinces
    3. Calculates scores for Districts
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def process_keyword(self, keyword_id: str):
        # Get keyword
        result = await self.db.execute(
            select(Keyword).where(Keyword.id == keyword_id)
        )
        keyword = result.scalar_one_or_none()

        if not keyword:
            logger.error(f"❌ Keyword {keyword_id} not found")
            return {"status": "error", "message": "Keyword not found"}

        keyword_text = keyword.keyword
        logger.info(f"📊 Processing keyword: '{keyword_text}'")

        # STEP 1: Clear existing data
        await cache_invalidate(f"geoint:*{keyword_id}*")
        await cache_invalidate(f"*{keyword_id}*")
        
        from sqlalchemy import delete
        delete_result = await self.db.execute(
            delete(GEOINTScore).where(GEOINTScore.keyword_id == keyword_id)
        )
        deleted_count = delete_result.rowcount
        await self.db.commit()
        logger.info(f"✅ Deleted {deleted_count} old scores")

        # Get provinces
        provinces_result = await self.db.execute(select(Province))
        provinces = provinces_result.scalars().all()

        if not provinces:
            logger.warning("⚠️ No provinces found")
            return {"status": "error", "message": "No provinces found"}

        # Initialize services
        trends_collector = GoogleTrendsCollector()
        economic_service = EconomicDataService()
        competition_analyzer = CompetitionAnalyzer(self.db)
        
        try:
            region_interest = await trends_collector.get_region_interest(keyword_text)
            interest_over_time = await trends_collector.get_interest_over_time(keyword_text)
            trend_metrics = await trends_collector.calculate_trend_metrics(interest_over_time)
        except Exception as e:
            logger.warning(f"⚠️ Trends collection failed: {e}. Using fallback.")
            region_interest = {}
            trend_metrics = {'yoy_change': 0, 'mom_change': 0}

        # Calculate Province Scores
        calculator = GEOINTCalculator(self.db)
        scores_created = 0
        province_metrics = {}

        for province in provinces:
            province_code = province.code.zfill(2)
            trends_data = region_interest.get(province_code, {})
            search_index = trends_data.get('value', 50)

            trend_data = {
                'yoy_change': trend_metrics.get('yoy_change', 0),
                'mom_change': trend_metrics.get('mom_change', 0)
            }

            economic_indicators = economic_service.get_economic_indicators(province.name)
            demographic_data = {
                'population': province.population or 500000,
                'income_index': economic_indicators['income_index'],
                'gdp_per_capita': economic_indicators['gdp_per_capita'],
                'development_tier': economic_indicators['development_tier'],
                'employment_rate': economic_indicators['employment_rate'],
                'data_source': 'TurkStat_2023'
            }

            competition_analysis = await competition_analyzer.analyze_competition(
                keyword=keyword_text,
                region_name=province.name,
                region_id=str(province.id)
            )

            competition_data = {
                'competitor_count': competition_analysis['competitor_count'],
                'avg_competitor_strength': competition_analysis['avg_competitor_strength'],
                'competition_density': competition_analysis['competition_density'],
                'market_saturation': competition_analysis['market_saturation'],
                'data_source': competition_analysis['data_source'],
                'real_data': competition_analysis['real_data']
            }

            province_metrics[str(province.id)] = {
                'search_index': search_index,
                'trend_data': trend_data,
                'demographic_data': demographic_data,
                'competition_data': competition_data
            }

            score = await calculator.calculate_score(
                keyword_id=keyword_id,
                region_id=str(province.id),
                region_type=RegionType.PROVINCE,
                search_index=search_index,
                trend_data=trend_data,
                demographic_data=demographic_data,
                competition_data=competition_data,
                region_name=province.name
            )
            self.db.add(score)
            scores_created += 1

        # Calculate District Scores
        logger.info("  ↳ Calculating district scores...")
        districts_result = await self.db.execute(select(District))
        districts = districts_result.scalars().all()
        logger.info(f"  ↳ Found {len(districts)} districts")

        for district in districts:
            p_metrics = province_metrics.get(str(district.province_id))
            if not p_metrics:
                continue
            
            d_demographic = p_metrics['demographic_data'].copy()
            d_demographic['population'] = district.population or 10000
            
            import random
            d_search_index = max(0, min(100, p_metrics['search_index'] + random.uniform(-5, 5)))
            
            d_score = await calculator.calculate_score(
                keyword_id=keyword_id,
                region_id=str(district.id),
                region_type=RegionType.DISTRICT,
                search_index=d_search_index,
                trend_data=p_metrics['trend_data'],
                demographic_data=d_demographic,
                competition_data=p_metrics['competition_data'],
                region_name=district.name
            )
            self.db.add(d_score)
            scores_created += 1

        await self.db.commit()
        logger.info(f"✅ Created {scores_created} total scores")
        
        await cache_invalidate(f"geoint:*{keyword_id}*")
        
        return {"status": "success", "scores_created": scores_created}
