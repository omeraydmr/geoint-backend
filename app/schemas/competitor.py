"""Competitor-related schemas"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================
# Request Schemas
# ============================================

class CompetitorCreate(BaseModel):
    """Create competitor request"""
    domain: str = Field(..., min_length=1, max_length=255, description="Competitor domain")
    name: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class CompetitorUpdate(BaseModel):
    """Update competitor request"""
    name: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class CompetitorAnalyzeRequest(BaseModel):
    """Request to analyze a competitor"""
    domain: str = Field(..., min_length=1, max_length=255)


class CompetitorCompareRequest(BaseModel):
    """Request to compare multiple competitors"""
    competitor_ids: List[UUID] = Field(..., min_length=2, max_length=4)
    user_domain: Optional[str] = None


class AIInsightsRequest(BaseModel):
    """Request AI-generated insights"""
    regenerate: bool = False  # Force regeneration even if cached


# ============================================
# Response Schemas
# ============================================

class CompetitorResponse(BaseModel):
    """Competitor response"""
    id: UUID
    user_id: UUID
    domain: str
    name: Optional[str] = None
    category: Optional[str] = None

    # SEO Metrics
    domain_authority: Optional[int] = None
    page_authority: Optional[int] = None
    trust_flow: Optional[int] = None
    citation_flow: Optional[int] = None

    # Traffic
    organic_traffic: Optional[int] = None
    organic_keywords: Optional[int] = None
    paid_keywords: Optional[int] = None

    # Backlinks
    total_backlinks: Optional[int] = None
    referring_domains: Optional[int] = None

    # Ad Intelligence (NEW)
    estimated_ad_spend: Optional[int] = None
    estimated_ad_keywords: Optional[int] = None
    content_score: Optional[int] = None

    # Social (NEW)
    social_followers: Optional[Dict] = None

    # Metadata
    technologies: Optional[Dict] = None
    social_media: Optional[Dict] = None
    notes: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_analyzed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompetitorSnapshotResponse(BaseModel):
    """Competitor snapshot response"""
    id: UUID
    competitor_id: UUID
    domain_authority: Optional[int] = None
    organic_traffic: Optional[int] = None
    organic_keywords: Optional[int] = None
    total_backlinks: Optional[int] = None
    referring_domains: Optional[int] = None
    top_keywords: Optional[List[Dict]] = None
    snapshot_date: datetime

    class Config:
        from_attributes = True


class CompetitorWithSnapshots(CompetitorResponse):
    """Competitor with historical snapshots"""
    snapshots: List[CompetitorSnapshotResponse] = Field(default_factory=list)


class CompetitorKeywordOverlap(BaseModel):
    """Keyword overlap analysis between user and competitor"""
    competitor_domain: str
    total_competitor_keywords: int
    overlapping_keywords: int
    overlap_percentage: float
    unique_to_competitor: int
    top_overlapping_keywords: List[Dict]  # [{keyword, user_position, competitor_position, search_volume}, ...]


class CompetitorGapAnalysis(BaseModel):
    """Keyword gap analysis"""
    competitor_domain: str
    total_gap_keywords: int
    high_value_gaps: List[Dict]  # [{keyword, search_volume, difficulty, estimated_traffic}, ...]
    content_gaps: List[Dict]  # [{topic, search_volume, competitor_url}, ...]


class CompetitorComparison(BaseModel):
    """Side-by-side competitor comparison"""
    user_domain: str
    competitors: List[CompetitorResponse]
    metrics_comparison: Dict  # {metric_name: {user: value, competitor1: value, ...}}
    rank_position: Dict  # {metric_name: rank (1 = best)}


class CompetitorInsights(BaseModel):
    """AI-generated competitor insights"""
    domain: str
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]
    recommendations: List[str]
    generated_at: datetime


# ============================================
# New Response Schemas (Advanced Features)
# ============================================

class CompetitorTrendPoint(BaseModel):
    """Single point in trend data"""
    date: datetime
    domain_authority: Optional[int] = None
    organic_traffic: Optional[int] = None
    organic_keywords: Optional[int] = None
    total_backlinks: Optional[int] = None
    referring_domains: Optional[int] = None


class CompetitorTrendsResponse(BaseModel):
    """Historical trend data for a competitor"""
    competitor_id: UUID
    domain: str
    time_range: str  # 7d, 30d, 90d, 1y
    data_points: List[CompetitorTrendPoint]
    growth_rates: Dict[str, float]  # {metric: percentage_change}


class BacklinkResponse(BaseModel):
    """Individual backlink entry"""
    id: UUID
    source_url: str
    source_domain: str
    target_url: Optional[str] = None
    anchor_text: Optional[str] = None
    domain_authority: Optional[int] = None
    page_authority: Optional[int] = None
    link_type: str = "dofollow"
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True


class BacklinkProfileResponse(BaseModel):
    """Complete backlink profile for a competitor"""
    competitor_id: UUID
    domain: str
    total_backlinks: int
    referring_domains: int
    dofollow_count: int
    nofollow_count: int
    top_anchor_texts: List[Dict[str, Any]]  # [{anchor, count, percentage}]
    top_referring_domains: List[Dict[str, Any]]  # [{domain, backlinks, da}]
    backlinks: List[BacklinkResponse]
    new_backlinks_30d: int
    lost_backlinks_30d: int


class ContentGapItem(BaseModel):
    """Individual content gap opportunity"""
    topic: str
    search_volume: int
    difficulty: Optional[int] = None
    competitor_url: Optional[str] = None
    content_type: str  # blog, landing, product, etc.
    opportunity_score: float


class ContentGapResponse(BaseModel):
    """Content gap analysis results"""
    competitor_id: UUID
    domain: str
    total_gaps: int
    content_gaps: List[ContentGapItem]
    top_performing_pages: List[Dict[str, Any]]  # [{url, traffic, keywords}]


class AdIntelligenceResponse(BaseModel):
    """Ad intelligence data"""
    competitor_id: UUID
    domain: str
    estimated_monthly_spend: Optional[int] = None
    estimated_ad_keywords: int
    top_ad_keywords: List[Dict[str, Any]]  # [{keyword, position, cpc, volume}]
    ad_copy_samples: List[Dict[str, Any]]  # [{headline, description, url}]
    display_ads_detected: int
    search_ads_detected: int


class TechStackResponse(BaseModel):
    """Technology stack detection"""
    competitor_id: UUID
    domain: str
    categories: Dict[str, List[str]]  # {category: [technologies]}
    cms: Optional[str] = None
    ecommerce: Optional[str] = None
    analytics: List[str] = []
    advertising: List[str] = []
    hosting: Optional[str] = None
    cdn: Optional[str] = None
    frameworks: List[str] = []
    detected_at: datetime


class MarketOverviewResponse(BaseModel):
    """Market overview with industry benchmarks"""
    total_competitors: int
    industry_benchmarks: Dict[str, Any]  # {metric: {avg, min, max, your_value}}
    market_leaders: List[Dict[str, Any]]  # [{domain, metric, value}]
    your_position: Dict[str, int]  # {metric: rank}
    growth_opportunities: List[str]


class CompetitorComparisonResponse(BaseModel):
    """Side-by-side comparison of multiple competitors"""
    user_domain: Optional[str] = None
    competitors: List[CompetitorResponse]
    metrics_comparison: Dict[str, Dict[str, Any]]  # {metric: {domain: value}}
    rankings: Dict[str, List[str]]  # {metric: [domains sorted by metric]}
    radar_data: List[Dict[str, Any]]  # For radar chart visualization
