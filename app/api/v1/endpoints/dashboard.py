"""
Dashboard API Endpoints

Provides aggregated data for the dashboard including:
- Statistics overview
- GEOINT score trends
- Keyword performance
- Regional distribution
- Strategy progress
- Activity feed
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict
import logging

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import (
    DashboardStats,
    GEOINTTrendResponse,
    KeywordPerformanceResponse,
    RegionalDistributionResponse,
    StrategyProgressResponse,
    ActivitiesResponse,
    DashboardOverview,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get main dashboard statistics

    Returns counts and averages for:
    - Total keywords
    - Active strategies
    - Total competitors
    - Average GEOINT score
    - Total regions analyzed
    """
    try:
        service = DashboardService(db, current_user.get('id'))
        stats = await service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard stats"
        )


@router.get("/geoint-trend", response_model=GEOINTTrendResponse)
async def get_geoint_trend(
    days: int = Query(30, ge=7, le=90, description="Number of days for trend"),
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get GEOINT score trend over time

    Returns daily average GEOINT scores for the specified period.
    """
    try:
        service = DashboardService(db, current_user.get('id'))
        trend = await service.get_geoint_trend(days)
        return trend
    except Exception as e:
        logger.error(f"Error getting GEOINT trend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get GEOINT trend"
        )


@router.get("/keyword-performance", response_model=KeywordPerformanceResponse)
async def get_keyword_performance(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get keyword performance data

    Returns performance metrics for all user keywords including
    average GEOINT scores and top performing regions.
    """
    try:
        service = DashboardService(db, current_user.get('id'))
        performance = await service.get_keyword_performance()
        return performance
    except Exception as e:
        logger.error(f"Error getting keyword performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get keyword performance"
        )


@router.get("/regional-distribution", response_model=RegionalDistributionResponse)
async def get_regional_distribution(
    region_type: str = Query("il", description="Region type: il, ilce, mahalle"),
    limit: int = Query(10, ge=1, le=50, description="Number of top regions"),
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get regional distribution of GEOINT scores

    Returns top regions by average GEOINT score.
    """
    try:
        service = DashboardService(db, current_user.get('id'))
        distribution = await service.get_regional_distribution(region_type, limit)
        return distribution
    except Exception as e:
        logger.error(f"Error getting regional distribution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get regional distribution"
        )


@router.get("/strategy-progress", response_model=StrategyProgressResponse)
async def get_strategy_progress(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get progress data for active strategies

    Returns progress metrics for active and draft strategies.
    """
    try:
        service = DashboardService(db, current_user.get('id'))
        progress = await service.get_strategy_progress()
        return progress
    except Exception as e:
        logger.error(f"Error getting strategy progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get strategy progress"
        )


@router.get("/activities", response_model=ActivitiesResponse)
async def get_activities(
    limit: int = Query(10, ge=1, le=50, description="Number of activities"),
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent user activities

    Returns the most recent activities for the activity feed.
    """
    try:
        service = DashboardService(db, current_user.get('id'))
        activities = await service.get_recent_activities(limit)
        return activities
    except Exception as e:
        logger.error(f"Error getting activities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get activities"
        )


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete dashboard overview

    Returns all dashboard data in a single response for initial page load.
    """
    try:
        service = DashboardService(db, current_user.get('id'))
        overview = await service.get_dashboard_overview()
        return overview
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard overview"
        )
