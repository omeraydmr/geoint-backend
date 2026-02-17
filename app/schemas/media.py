"""Media monitoring and PR schemas"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum
from uuid import UUID


class SentimentEnum(str, Enum):
    """Sentiment classification"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class PROutcomeEnum(str, Enum):
    """PR opportunity outcome"""
    COVERAGE = "coverage"
    DECLINED = "declined"
    PENDING = "pending"
    NO_RESPONSE = "no_response"


# ============================================
# Media Mention Schemas
# ============================================

class MediaMentionCreate(BaseModel):
    """Create media mention request"""
    brand_query: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., min_length=1, max_length=1000)
    publication: Optional[str] = Field(None, max_length=255)
    author: Optional[str] = Field(None, max_length=255)
    excerpt: Optional[str] = None
    full_text: Optional[str] = None
    published_at: Optional[datetime] = None


class MediaMentionUpdate(BaseModel):
    """Update media mention request"""
    sentiment: Optional[SentimentEnum] = None
    sentiment_score: Optional[float] = Field(None, ge=-1, le=1)
    estimated_reach: Optional[int] = Field(None, ge=0)
    social_shares: Optional[int] = Field(None, ge=0)


class MediaMentionResponse(BaseModel):
    """Media mention response"""
    id: UUID
    user_id: UUID
    brand_query: str
    title: str
    url: str
    publication: Optional[str] = None
    author: Optional[str] = None
    excerpt: Optional[str] = None
    full_text: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    estimated_reach: Optional[int] = None
    social_shares: Optional[int] = None
    published_at: Optional[datetime] = None
    discovered_at: datetime

    class Config:
        from_attributes = True


class MediaMentionSearchRequest(BaseModel):
    """Search for media mentions"""
    brand_query: str = Field(..., min_length=1, max_length=255)
    days_back: int = Field(7, ge=1, le=90, description="How many days to search back")
    sources: Optional[List[str]] = Field(None, description="Specific publications to search")


# ============================================
# PR Opportunity Schemas
# ============================================

class PROpportunityCreate(BaseModel):
    """Create PR opportunity request"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    publication: Optional[str] = Field(None, max_length=255)
    relevance_score: Optional[float] = Field(None, ge=0, le=100)
    category: Optional[str] = Field(None, max_length=100)
    journalist_name: Optional[str] = Field(None, max_length=255)
    journalist_email: Optional[str] = Field(None, max_length=255)
    journalist_twitter: Optional[str] = Field(None, max_length=100)
    expires_at: Optional[datetime] = None


class PROpportunityUpdate(BaseModel):
    """Update PR opportunity request"""
    contacted: Optional[bool] = None
    response_received: Optional[bool] = None
    outcome: Optional[PROutcomeEnum] = None


class PROpportunityResponse(BaseModel):
    """PR opportunity response"""
    id: UUID
    user_id: UUID
    title: str
    description: Optional[str] = None
    publication: Optional[str] = None
    relevance_score: Optional[float] = None
    category: Optional[str] = None
    journalist_name: Optional[str] = None
    journalist_email: Optional[str] = None
    journalist_twitter: Optional[str] = None
    contacted: bool
    contacted_at: Optional[datetime] = None
    response_received: bool
    outcome: Optional[str] = None
    identified_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================
# Analytics Schemas
# ============================================

class MediaAnalytics(BaseModel):
    """Media monitoring analytics"""
    total_mentions: int
    positive_mentions: int
    negative_mentions: int
    neutral_mentions: int
    total_reach: int
    total_shares: int
    avg_sentiment_score: float
    top_publications: List[dict]  # [{publication, count}, ...]
    mentions_by_day: List[dict]  # [{date, count}, ...]


class PRPerformance(BaseModel):
    """PR opportunity performance"""
    total_opportunities: int
    contacted: int
    coverage_obtained: int
    conversion_rate: float
    top_publications: List[dict]
    top_categories: List[dict]
