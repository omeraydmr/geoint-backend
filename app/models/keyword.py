"""Keyword tracking models"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from app.core.database import Base


class Keyword(Base):
    """Keywords tracked by users"""
    __tablename__ = "keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Keyword data
    keyword = Column(String(255), nullable=False, index=True)
    root_form = Column(String(255))  # Turkish root form from Zemberek
    intent = Column(String(50))  # transactional, informational, commercial, navigational

    # Search data
    avg_monthly_searches = Column(Integer, default=0)
    search_trend = Column(String(10))  # 'increasing', 'decreasing', 'stable'
    cpc_avg = Column(Integer)  # TL (in kuruş)

    # Settings
    is_active = Column(Boolean, default=True)
    refresh_frequency = Column(String(20), default='daily')  # daily, weekly, monthly

    # Metadata
    nlp_metadata = Column(JSONB)  # Morphological analysis, synonyms, etc.
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_refreshed_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="keywords")
    geoint_scores = relationship("GEOINTScore", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Keyword '{self.keyword}' ({self.intent})>"
