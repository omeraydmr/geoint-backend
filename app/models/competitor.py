"""Competitor intelligence models"""
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from app.core.database import Base


class Competitor(Base):
    """Competitor domains tracked by users"""
    __tablename__ = "competitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Competitor info
    domain = Column(String(255), nullable=False, index=True)
    name = Column(String(255))
    category = Column(String(100))

    # Current metrics (updated periodically)
    domain_authority = Column(Integer)
    page_authority = Column(Integer)
    trust_flow = Column(Integer)
    citation_flow = Column(Integer)

    # Traffic estimates
    organic_traffic = Column(Integer)  # Monthly organic traffic estimate
    organic_keywords = Column(Integer)  # Number of ranking keywords
    paid_keywords = Column(Integer)

    # Backlinks
    total_backlinks = Column(Integer)
    referring_domains = Column(Integer)

    # Ad Intelligence (NEW)
    estimated_ad_spend = Column(Integer)  # Monthly estimated ad spend
    estimated_ad_keywords = Column(Integer)  # Number of paid keywords
    content_score = Column(Integer)  # Content quality score 0-100

    # Social Media (enhanced JSONB)
    social_followers = Column(JSONB)  # {twitter, linkedin, facebook, instagram}

    # AI Insights cache (NEW)
    ai_insights = Column(JSONB)  # Cached AI-generated SWOT analysis

    # Additional metadata
    technologies = Column(JSONB)  # Technologies used (from BuiltWith/Wappalyzer)
    social_media = Column(JSONB)  # Social media profiles and metrics
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_analyzed_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="competitors")
    snapshots = relationship("CompetitorSnapshot", back_populates="competitor", cascade="all, delete-orphan")
    backlinks = relationship("CompetitorBacklink", back_populates="competitor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Competitor {self.domain}>"


class CompetitorSnapshot(Base):
    """Historical snapshots of competitor metrics"""
    __tablename__ = "competitor_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id = Column(UUID(as_uuid=True), ForeignKey('competitors.id', ondelete='CASCADE'), nullable=False)

    # Snapshot metrics
    domain_authority = Column(Integer)
    organic_traffic = Column(Integer)
    organic_keywords = Column(Integer)
    total_backlinks = Column(Integer)
    referring_domains = Column(Integer)

    # Top ranking keywords (sample)
    top_keywords = Column(JSONB)  # [{keyword, position, search_volume, url}, ...]

    # Timestamp
    snapshot_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    competitor = relationship("Competitor", back_populates="snapshots")

    def __repr__(self):
        return f"<CompetitorSnapshot {self.competitor_id[:8]}... @ {self.snapshot_date}>"


class CompetitorBacklink(Base):
    """Detailed backlink profile for competitors"""
    __tablename__ = "competitor_backlinks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id = Column(UUID(as_uuid=True), ForeignKey('competitors.id', ondelete='CASCADE'), nullable=False)

    # Backlink details
    source_url = Column(String(2048), nullable=False)
    source_domain = Column(String(255), nullable=False, index=True)
    target_url = Column(String(2048))
    anchor_text = Column(String(500))

    # Authority metrics
    domain_authority = Column(Integer)
    page_authority = Column(Integer)

    # Link attributes
    link_type = Column(String(20), default='dofollow')  # dofollow, nofollow, ugc, sponsored
    is_image = Column(Integer, default=0)  # 0 or 1

    # Timestamps
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    # Relationships
    competitor = relationship("Competitor", back_populates="backlinks")

    def __repr__(self):
        return f"<CompetitorBacklink {self.source_domain} -> {self.competitor_id[:8]}...>"


class CompetitorComparisonHistory(Base):
    """Historical snapshots of competitor SERP comparisons"""
    __tablename__ = "competitor_comparison_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    keyword_id = Column(UUID(as_uuid=True), ForeignKey('keywords.id', ondelete='CASCADE'), nullable=False)
    user_domain = Column(String(255))
    competitor_domains = Column(JSONB, nullable=False)
    region_type = Column(String(10), default='il')
    results = Column(JSONB, nullable=False)
    summary = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CompetitorComparisonHistory {str(self.id)[:8]}... @ {self.created_at}>"
