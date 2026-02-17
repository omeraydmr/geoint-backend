"""Keyword-related schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class KeywordBase(BaseModel):
    """Base keyword schema"""
    keyword: str = Field(..., min_length=1, max_length=255)
    notes: Optional[str] = None


class KeywordCreate(KeywordBase):
    """Create keyword request"""
    pass


class KeywordUpdate(BaseModel):
    """Update keyword request"""
    keyword: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    refresh_frequency: Optional[str] = None
    notes: Optional[str] = None


class KeywordResponse(BaseModel):
    """Keyword response"""
    id: UUID
    user_id: UUID
    keyword: str
    root_form: Optional[str] = None
    intent: Optional[str] = None
    avg_monthly_searches: int
    search_trend: Optional[str] = None
    cpc_avg: Optional[int] = None
    is_active: bool
    refresh_frequency: str
    nlp_metadata: Optional[dict] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_refreshed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KeywordWithScores(KeywordResponse):
    """Keyword with GEOINT scores"""
    top_region: Optional[str] = None
    avg_geoint_score: Optional[float] = None
    total_regions_analyzed: Optional[int] = None
