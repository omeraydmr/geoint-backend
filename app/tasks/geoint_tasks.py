"""GEOINT-related background tasks (APScheduler)"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import select, and_
from app.core.database import async_session_maker
from app.models.keyword import Keyword
from app.models.geo import GEOINTScore
from app.services.geoint.processor import GEOINTProcessor

logger = logging.getLogger(__name__)


async def collect_all_trends():
    """
    Collect Google Trends data for all active keywords
    """
    logger.info("🔄 Starting trends collection for all keywords...")

    async with async_session_maker() as db:
        result = await db.execute(
            select(Keyword).where(Keyword.is_active == True)
        )
        keywords = result.scalars().all()

        processor = GEOINTProcessor(db)
        
        for keyword in keywords:
            try:
                await processor.process_keyword(str(keyword.id))
            except Exception as e:
                logger.error(f"Error processing keyword {keyword.keyword}: {e}")

    logger.info(f"✅ Completed trends collection for {len(keywords)} keywords")
    return {"status": "success", "keywords_processed": len(keywords)}


async def update_all_scores():
    """
    Recalculate GEOINT scores for all keywords
    """
    logger.info("🔄 Updating GEOINT scores...")

    async with async_session_maker() as db:
        result = await db.execute(
            select(Keyword).where(Keyword.is_active == True)
        )
        keywords = result.scalars().all()

        processor = GEOINTProcessor(db)

        for keyword in keywords:
            try:
                await processor.process_keyword(str(keyword.id))
            except Exception as e:
                logger.error(f"Error updating score for {keyword.keyword}: {e}")

    logger.info(f"✅ Completed score update for {len(keywords)} keywords")
    return {"status": "success", "keywords_processed": len(keywords)}


async def check_alerts():
    """
    Check for significant changes in GEOINT scores and send alerts
    """
    logger.info("🔔 Checking for GEOINT alerts...")

    alerts = []

    async with async_session_maker() as db:
        # Find scores with significant trend changes
        result = await db.execute(
            select(GEOINTScore).where(
                and_(
                    GEOINTScore.trend_change_pct > 20,  # More than 20% increase
                    GEOINTScore.calculated_at >= datetime.utcnow() - timedelta(hours=24)
                )
            )
        )
        high_growth_scores = result.scalars().all()

        for score in high_growth_scores:
            alerts.append({
                "type": "high_growth",
                "keyword_id": str(score.keyword_id),
                "region_id": str(score.region_id),
                "change_pct": score.trend_change_pct
            })

    logger.info(f"✅ Alert check completed, found {len(alerts)} alerts")
    return {"status": "success", "alerts": len(alerts)}


async def process_keyword(keyword_id: str):
    """
    Process a single keyword: collect data and calculate scores
    Used for direct calls or manual triggers.
    """
    logger.info(f"🔄 Processing keyword {keyword_id}...")
    
    async with async_session_maker() as db:
        processor = GEOINTProcessor(db)
        return await processor.process_keyword(keyword_id)