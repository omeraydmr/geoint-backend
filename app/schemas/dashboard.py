"""Dashboard Pydantic schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ActivityType(str, Enum):
    """Activity type enumeration"""
    KEYWORD_ADDED = "keyword_added"
    KEYWORD_DELETED = "keyword_deleted"
    STRATEGY_CREATED = "strategy_created"
    STRATEGY_UPDATED = "strategy_updated"
    COMPETITOR_ADDED = "competitor_added"
    COMPETITOR_ANALYZED = "competitor_analyzed"
    GEOINT_CALCULATED = "geoint_calculated"
    ALERT_TRIGGERED = "alert_triggered"


# ============================================
# Dashboard Stats
# ============================================

class DashboardStats(BaseModel):
    """Main dashboard statistics"""
    total_keywords: int = Field(..., description="Total tracked keywords")
    active_strategies: int = Field(..., description="Active strategies count")
    total_competitors: int = Field(..., description="Total tracked competitors")
    avg_geoint_score: float = Field(..., description="Average GEOINT score across all keywords")
    total_regions_analyzed: int = Field(..., description="Total regions with GEOINT data")

    # Changes from previous period
    keywords_change: int = Field(0, description="Change in keywords count")
    strategies_change: int = Field(0, description="Change in strategies count")
    competitors_change: int = Field(0, description="Change in competitors count")
    geoint_score_change: float = Field(0, description="Change in avg GEOINT score")


# ============================================
# Chart Data Schemas
# ============================================

class TrendDataPoint(BaseModel):
    """Single data point for trend chart"""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    value: float = Field(..., description="Value at this date")
    label: Optional[str] = None


class GEOINTTrendResponse(BaseModel):
    """GEOINT score trend over time"""
    data: List[TrendDataPoint]
    period_start: str
    period_end: str
    average_score: float
    trend_direction: str  # 'up', 'down', 'stable'
    change_percentage: float


class KeywordPerformanceItem(BaseModel):
    """Keyword performance data"""
    keyword_id: str
    keyword: str
    avg_geoint_score: float
    top_region: Optional[str] = None
    top_region_score: float = 0
    trend_direction: str = "stable"
    regions_count: int = 0


class KeywordPerformanceResponse(BaseModel):
    """Keyword performance chart data"""
    keywords: List[KeywordPerformanceItem]
    total_keywords: int


class RegionDistributionItem(BaseModel):
    """Region distribution data"""
    region_id: str
    region_name: str
    region_type: str
    avg_score: float
    keywords_count: int
    percentage: float


class RegionalDistributionResponse(BaseModel):
    """Regional distribution chart data"""
    regions: List[RegionDistributionItem]
    total_regions: int
    region_type: str


class StrategyProgressItem(BaseModel):
    """Strategy progress data"""
    strategy_id: str
    name: str
    status: str
    completion_percentage: int
    tasks_completed: int
    tasks_total: int
    budget_spent: float
    budget_total: float
    days_remaining: int


class StrategyProgressResponse(BaseModel):
    """Strategy progress chart data"""
    strategies: List[StrategyProgressItem]
    total_active: int


# ============================================
# Activity Feed
# ============================================

class ActivityItem(BaseModel):
    """Single activity item"""
    id: str
    activity_type: ActivityType
    title: str
    description: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ActivitiesResponse(BaseModel):
    """Activities feed response"""
    activities: List[ActivityItem]
    total_count: int
    has_more: bool


# ============================================
# Complete Dashboard Response
# ============================================

class DashboardOverview(BaseModel):
    """Complete dashboard overview combining all data"""
    stats: DashboardStats
    geoint_trend: Optional[GEOINTTrendResponse] = None
    keyword_performance: Optional[KeywordPerformanceResponse] = None
    regional_distribution: Optional[RegionalDistributionResponse] = None
    strategy_progress: Optional[StrategyProgressResponse] = None
    recent_activities: Optional[ActivitiesResponse] = None
