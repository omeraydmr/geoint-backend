"""Dashboard data aggregation service"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, Integer
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

from app.models.keyword import Keyword
from app.models.competitor import Competitor
from app.models.strategy import Strategy, StrategyStatus, StrategyWeek, StrategyTask, TaskStatus
from app.models.geo import GEOINTScore, Province, RegionType
from app.models.activity import Activity, ActivityType
from app.schemas.dashboard import (
    DashboardStats,
    GEOINTTrendResponse,
    TrendDataPoint,
    KeywordPerformanceResponse,
    KeywordPerformanceItem,
    RegionalDistributionResponse,
    RegionDistributionItem,
    StrategyProgressResponse,
    StrategyProgressItem,
    ActivitiesResponse,
    ActivityItem,
    DashboardOverview,
)

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for aggregating dashboard data"""

    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id

    async def get_stats(self) -> DashboardStats:
        """Get main dashboard statistics"""
        # Count keywords
        keywords_result = await self.db.execute(
            select(func.count(Keyword.id)).where(Keyword.user_id == self.user_id)
        )
        total_keywords = keywords_result.scalar() or 0

        # Count active strategies
        strategies_result = await self.db.execute(
            select(func.count(Strategy.id)).where(
                and_(
                    Strategy.user_id == self.user_id,
                    Strategy.status == StrategyStatus.ACTIVE
                )
            )
        )
        active_strategies = strategies_result.scalar() or 0

        # Count competitors
        competitors_result = await self.db.execute(
            select(func.count(Competitor.id)).where(Competitor.user_id == self.user_id)
        )
        total_competitors = competitors_result.scalar() or 0

        # Calculate average GEOINT score
        avg_score_result = await self.db.execute(
            select(func.avg(GEOINTScore.geoint_score)).where(
                GEOINTScore.keyword_id.in_(
                    select(Keyword.id).where(Keyword.user_id == self.user_id)
                )
            )
        )
        avg_geoint_score = avg_score_result.scalar() or 0

        # Count regions with data
        regions_result = await self.db.execute(
            select(func.count(func.distinct(GEOINTScore.region_id))).where(
                GEOINTScore.keyword_id.in_(
                    select(Keyword.id).where(Keyword.user_id == self.user_id)
                )
            )
        )
        total_regions = regions_result.scalar() or 0

        return DashboardStats(
            total_keywords=total_keywords,
            active_strategies=active_strategies,
            total_competitors=total_competitors,
            avg_geoint_score=round(avg_geoint_score, 1),
            total_regions_analyzed=total_regions,
            keywords_change=0,
            strategies_change=0,
            competitors_change=0,
            geoint_score_change=0,
        )

    async def get_geoint_trend(self, days: int = 30) -> GEOINTTrendResponse:
        """Get GEOINT score trend over time"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Get user's keyword IDs
        keywords_result = await self.db.execute(
            select(Keyword.id).where(Keyword.user_id == self.user_id)
        )
        keyword_ids = [row[0] for row in keywords_result.fetchall()]

        if not keyword_ids:
            return GEOINTTrendResponse(
                data=[],
                period_start=start_date.strftime("%Y-%m-%d"),
                period_end=end_date.strftime("%Y-%m-%d"),
                average_score=0,
                trend_direction="stable",
                change_percentage=0,
            )

        # Get daily average scores
        scores_result = await self.db.execute(
            select(
                func.date(GEOINTScore.calculated_at).label("date"),
                func.avg(GEOINTScore.geoint_score).label("avg_score")
            ).where(
                and_(
                    GEOINTScore.keyword_id.in_(keyword_ids),
                    GEOINTScore.calculated_at >= start_date
                )
            ).group_by(func.date(GEOINTScore.calculated_at))
            .order_by(func.date(GEOINTScore.calculated_at))
        )

        data_points = []
        scores = []
        for row in scores_result.fetchall():
            score = round(float(row.avg_score), 1)
            scores.append(score)
            data_points.append(TrendDataPoint(
                date=row.date.strftime("%Y-%m-%d"),
                value=score,
            ))

        # Calculate trend
        avg_score = sum(scores) / len(scores) if scores else 0
        if len(scores) >= 2:
            first_half_avg = sum(scores[:len(scores)//2]) / (len(scores)//2)
            second_half_avg = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            change_pct = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0

            if change_pct > 5:
                trend_direction = "up"
            elif change_pct < -5:
                trend_direction = "down"
            else:
                trend_direction = "stable"
        else:
            change_pct = 0
            trend_direction = "stable"

        return GEOINTTrendResponse(
            data=data_points,
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
            average_score=round(avg_score, 1),
            trend_direction=trend_direction,
            change_percentage=round(change_pct, 1),
        )

    async def get_keyword_performance(self) -> KeywordPerformanceResponse:
        """Get performance data for all keywords"""
        # Get keywords with their GEOINT stats
        result = await self.db.execute(
            select(
                Keyword.id,
                Keyword.keyword,
                func.avg(GEOINTScore.geoint_score).label("avg_score"),
                func.count(GEOINTScore.id).label("regions_count")
            ).outerjoin(
                GEOINTScore, Keyword.id == GEOINTScore.keyword_id
            ).where(
                Keyword.user_id == self.user_id
            ).group_by(Keyword.id, Keyword.keyword)
            .order_by(desc(func.avg(GEOINTScore.geoint_score)))
        )

        keywords = []
        for row in result.fetchall():
            # Get top region for this keyword
            top_region_result = await self.db.execute(
                select(GEOINTScore.region_id, GEOINTScore.geoint_score, Province.name)
                .join(Province, Province.id == GEOINTScore.region_id)
                .where(GEOINTScore.keyword_id == row.id)
                .order_by(desc(GEOINTScore.geoint_score))
                .limit(1)
            )
            top_region_row = top_region_result.fetchone()

            keywords.append(KeywordPerformanceItem(
                keyword_id=str(row.id),
                keyword=row.keyword,
                avg_geoint_score=round(float(row.avg_score or 0), 1),
                top_region=top_region_row.name if top_region_row else None,
                top_region_score=round(float(top_region_row.geoint_score), 1) if top_region_row else 0,
                trend_direction="stable",
                regions_count=row.regions_count or 0,
            ))

        return KeywordPerformanceResponse(
            keywords=keywords,
            total_keywords=len(keywords),
        )

    async def get_regional_distribution(
        self,
        region_type: str = "il",
        limit: int = 10
    ) -> RegionalDistributionResponse:
        """Get distribution of GEOINT scores by region"""
        # Get user's keyword IDs
        keywords_result = await self.db.execute(
            select(Keyword.id).where(Keyword.user_id == self.user_id)
        )
        keyword_ids = [row[0] for row in keywords_result.fetchall()]

        if not keyword_ids:
            return RegionalDistributionResponse(
                regions=[],
                total_regions=0,
                region_type=region_type,
            )

        # Map frontend values to DB enum
        # This handles the case where DB expects uppercase PROVINCE/DISTRICT but frontend sends il/ilce
        region_type_map = {
            "il": RegionType.PROVINCE,
            "ilce": RegionType.DISTRICT,
            "mahalle": RegionType.NEIGHBORHOOD
        }
        db_region_type = region_type_map.get(region_type, RegionType.PROVINCE)

        # Get regions with aggregated data
        result = await self.db.execute(
            select(
                Province.id,
                Province.name,
                func.avg(GEOINTScore.geoint_score).label("avg_score"),
                func.count(func.distinct(GEOINTScore.keyword_id)).label("keywords_count")
            ).join(
                GEOINTScore, Province.id == GEOINTScore.region_id
            ).where(
                and_(
                    GEOINTScore.keyword_id.in_(keyword_ids),
                    GEOINTScore.region_type == db_region_type
                )
            ).group_by(Province.id, Province.name)
            .order_by(desc(func.avg(GEOINTScore.geoint_score)))
            .limit(limit)
        )

        regions = []
        total_score = 0
        rows = result.fetchall()

        for row in rows:
            total_score += float(row.avg_score or 0)

        for row in rows:
            percentage = (float(row.avg_score or 0) / total_score * 100) if total_score > 0 else 0
            regions.append(RegionDistributionItem(
                region_id=str(row.id),
                region_name=row.name,
                region_type=region_type,
                avg_score=round(float(row.avg_score or 0), 1),
                keywords_count=row.keywords_count,
                percentage=round(percentage, 1),
            ))

        return RegionalDistributionResponse(
            regions=regions,
            total_regions=len(regions),
            region_type=region_type,
        )

    async def get_strategy_progress(self) -> StrategyProgressResponse:
        """Get progress data for active strategies"""
        result = await self.db.execute(
            select(Strategy).where(
                and_(
                    Strategy.user_id == self.user_id,
                    Strategy.status.in_([StrategyStatus.ACTIVE, StrategyStatus.DRAFT])
                )
            ).order_by(desc(Strategy.created_at))
            .limit(5)
        )

        strategies = []
        for strategy in result.scalars().all():
            # Calculate days remaining
            if strategy.end_date:
                days_remaining = max(0, (strategy.end_date - datetime.utcnow()).days)
            else:
                days_remaining = 0

            # Count tasks
            tasks_result = await self.db.execute(
                select(
                    func.count(StrategyTask.id).label("total"),
                    func.sum(
                        func.cast(StrategyTask.status == TaskStatus.COMPLETED, type_=Integer)
                    ).label("completed")
                ).join(
                    StrategyWeek, StrategyTask.week_id == StrategyWeek.id
                ).where(StrategyWeek.strategy_id == strategy.id)
            )
            tasks_row = tasks_result.fetchone()

            # Calculate completion from actual task data (not stale DB value)
            tasks_completed = int(tasks_row.completed or 0) if tasks_row else 0
            tasks_total = int(tasks_row.total or 0) if tasks_row else 0
            calculated_completion = round((tasks_completed / tasks_total) * 100) if tasks_total > 0 else 0

            strategies.append(StrategyProgressItem(
                strategy_id=str(strategy.id),
                name=strategy.name,
                status=strategy.status.value,
                completion_percentage=calculated_completion,
                tasks_completed=tasks_completed,
                tasks_total=tasks_total,
                budget_spent=strategy.budget_spent or 0,
                budget_total=strategy.total_budget or 0,
                days_remaining=days_remaining,
            ))

        active_count = len([s for s in strategies if s.status == "ACTIVE"])

        return StrategyProgressResponse(
            strategies=strategies,
            total_active=active_count,
        )

    async def get_recent_activities(self, limit: int = 10) -> ActivitiesResponse:
        """Get recent user activities"""
        result = await self.db.execute(
            select(Activity).where(
                Activity.user_id == self.user_id
            ).order_by(desc(Activity.created_at))
            .limit(limit + 1)  # Get one extra to check if there are more
        )

        activities_list = result.scalars().all()
        has_more = len(activities_list) > limit
        activities_list = activities_list[:limit]

        activities = [
            ActivityItem(
                id=str(a.id),
                activity_type=a.activity_type,
                title=a.title,
                description=a.description or "",
                timestamp=a.created_at,
                metadata=getattr(a, "activity_metadata", None),
            )
            for a in activities_list
        ]

        # Get total count
        count_result = await self.db.execute(
            select(func.count(Activity.id)).where(Activity.user_id == self.user_id)
        )
        total_count = count_result.scalar() or 0

        return ActivitiesResponse(
            activities=activities,
            total_count=total_count,
            has_more=has_more,
        )

    async def get_dashboard_overview(self) -> DashboardOverview:
        """Get complete dashboard overview"""
        stats = await self.get_stats()
        geoint_trend = await self.get_geoint_trend()
        keyword_performance = await self.get_keyword_performance()
        regional_distribution = await self.get_regional_distribution()
        strategy_progress = await self.get_strategy_progress()
        recent_activities = await self.get_recent_activities()

        return DashboardOverview(
            stats=stats,
            geoint_trend=geoint_trend,
            keyword_performance=keyword_performance,
            regional_distribution=regional_distribution,
            strategy_progress=strategy_progress,
            recent_activities=recent_activities,
        )


async def log_activity(
    db: AsyncSession,
    user_id: str,
    activity_type: ActivityType,
    title: str,
    description: str = None,
    entity_type: str = None,
    entity_id: str = None,
    metadata: dict = None
):
    """Helper function to log user activity"""
    activity = Activity(
        user_id=user_id,
        activity_type=activity_type,
        title=title,
        description=description,
        entity_type=entity_type,
        entity_id=entity_id,
        # activity_metadata=metadata,  # Column missing in DB
    )
    db.add(activity)
    await db.commit()
