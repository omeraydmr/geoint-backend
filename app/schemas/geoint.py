"""GEOINT-related Pydantic schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RegionTypeEnum(str, Enum):
    """Region type enumeration"""
    PROVINCE = "il"
    DISTRICT = "ilce"
    NEIGHBORHOOD = "mahalle"


# ============================================
# Request Schemas
# ============================================

class BudgetRecommendationRequest(BaseModel):
    """Request for budget allocation recommendation"""
    keyword_id: str = Field(..., description="Keyword UUID")
    total_budget: float = Field(..., gt=0, description="Total budget in TL")
    region_type: RegionTypeEnum = Field(RegionTypeEnum.PROVINCE, description="Region type")
    top_n: int = Field(10, ge=1, le=50, description="Number of top regions")


class KeywordAnalysisRequest(BaseModel):
    """Request for keyword NLP analysis"""
    keyword: str = Field(..., min_length=1, max_length=255)


# ============================================
# Response Schemas
# ============================================

class GEOINTScoreResponse(BaseModel):
    """GEOINT score details"""
    id: str
    keyword_id: str
    region_type: str
    region_id: str
    region_name: Optional[str] = None

    # Score components
    search_index: float
    trend_score: float
    demographic_fit: float
    competition_gap: float
    geoint_score: float

    # Trend info
    trend_direction: Optional[str] = None
    trend_change_pct: Optional[float] = None

    # Metadata
    calculated_at: datetime

    class Config:
        from_attributes = True


class TopRegionResponse(BaseModel):
    """Top region summary"""
    region_id: str
    region_name: str
    region_type: str
    geoint_score: float
    search_index: float
    trend_score: float
    demographic_fit: float
    competition_gap: float
    trend_direction: str
    calculated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BudgetAllocation(BaseModel):
    """Budget allocation for a region"""
    region_id: str
    region_name: str
    region_type: str
    geoint_score: float
    allocated_budget: float
    allocation_percentage: float
    recommended_channels: List[str]

    # Score breakdown
    search_index: float
    trend_score: float
    demographic_fit: float
    competition_gap: float

    class Config:
        from_attributes = True


class HeatmapMetadata(BaseModel):
    """Heatmap metadata"""
    keyword_id: str
    region_type: str
    total_regions: int
    regions_with_data: int


class HeatmapResponse(BaseModel):
    """Complete heatmap response"""
    type: str = "FeatureCollection"
    features: List[Dict[str, Any]]
    metadata: HeatmapMetadata


# ============================================
# Analytics Schemas
# ============================================

class TrendMetrics(BaseModel):
    """Trend analysis metrics"""
    yoy_change: float = Field(..., description="Year-over-year % change")
    mom_change: float = Field(..., description="Month-over-month % change")
    trend: str = Field(..., description="rising, declining, or stable")
    avg_interest: float
    current_interest: float
    peak_interest: float


class RegionInterest(BaseModel):
    """Regional interest data from Google Trends"""
    region_code: str
    region_name: str
    interest_value: int = Field(..., ge=0, le=100)


class KeywordAnalysisResponse(BaseModel):
    """NLP analysis result"""
    keyword: str
    root_form: str
    intent: str
    pos: Optional[str] = None
    is_valid: bool
    variations: List[str]
    similar_keywords: Optional[List[str]] = None


# ============================================
# Google Ads Schemas
# ============================================

class AdPerformanceMetrics(BaseModel):
    """Ad performance metrics"""
    impressions: int
    clicks: int
    ctr: float = Field(..., description="Click-through rate")
    avg_cpc: float = Field(..., description="Average cost per click in TL")
    cost: float = Field(..., description="Total cost in TL")
    conversions: int
    conversion_rate: float
    roas: Optional[float] = Field(None, description="Return on ad spend")


class GoogleAdsKeywordMetrics(BaseModel):
    """Google Ads keyword metrics"""
    keyword: str
    search_volume: int
    competition: str  # LOW, MEDIUM, HIGH
    cpc_low: float
    cpc_high: float
    cpc_avg: float


class AdRecommendation(BaseModel):
    """Ad campaign recommendation"""
    region_name: str
    platform: str  # google, meta, etc.
    daily_budget: float
    estimated_impressions: int
    estimated_clicks: int
    estimated_conversions: int
    recommended_bid: float


# ============================================
# Competitor Comparison Schemas
# ============================================

class RegionCompetitorData(BaseModel):
    """SERP position comparison data for a single region"""
    region_id: str = Field(..., description="Province/district code")
    region_name: str = Field(..., description="Province/district name")
    positions: Dict[str, Optional[int]] = Field(
        ...,
        description="Map of domain to SERP position (None if not in top results)"
    )
    your_position: Optional[int] = Field(None, description="Your domain's position")
    best_competitor_position: Optional[int] = Field(
        None, description="Best competitor position in this region"
    )
    position_gap: Optional[int] = Field(
        None,
        description="Gap between your position and best competitor (negative = you're behind)"
    )

    class Config:
        from_attributes = True


class CompetitorComparisonSummary(BaseModel):
    """Summary statistics for competitor comparison"""
    total_regions: int = Field(..., description="Total regions analyzed")
    regions_with_your_data: int = Field(..., description="Regions where you rank")
    winning_regions: int = Field(
        ..., description="Regions where you outrank all competitors"
    )
    losing_regions: int = Field(
        ..., description="Regions where at least one competitor outranks you"
    )
    tied_regions: int = Field(..., description="Regions with same position")
    not_ranking_regions: int = Field(
        ..., description="Regions where you don't appear in results"
    )
    avg_position: Optional[float] = Field(None, description="Your average position")
    avg_competitor_position: Optional[float] = Field(
        None, description="Average best competitor position"
    )

    class Config:
        from_attributes = True


class CompetitorComparisonResponse(BaseModel):
    """Complete competitor comparison response"""
    keyword_id: str
    keyword: str
    user_domain: Optional[str] = None
    competitors: List[str] = Field(..., description="List of competitor domains")
    regions: List[RegionCompetitorData]
    summary: CompetitorComparisonSummary

    class Config:
        from_attributes = True


class ComparisonHistoryItem(BaseModel):
    """Summary item for comparison history list"""
    id: str
    user_domain: Optional[str] = None
    competitor_domains: List[str]
    region_type: str
    summary: CompetitorComparisonSummary
    created_at: str  # ISO format datetime string

    class Config:
        from_attributes = True


class ComparisonHistoryListResponse(BaseModel):
    """List of historical comparisons for a keyword"""
    keyword_id: str
    comparisons: List[ComparisonHistoryItem]
