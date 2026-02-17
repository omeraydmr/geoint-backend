"""Media monitoring and PR intelligence models"""
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from app.core.database import Base


class MediaMention(Base):
    """Media mentions and brand coverage"""
    __tablename__ = "media_mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))

    # Mention details
    brand_query = Column(String(255), nullable=False)  # What we searched for
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    publication = Column(String(255))  # 'Webrazzi', 'ShiftDelete', etc.
    author = Column(String(255))

    # Content
    excerpt = Column(Text)
    full_text = Column(Text)

    # Sentiment analysis
    sentiment = Column(String(20))  # 'positive', 'negative', 'neutral'
    sentiment_score = Column(Float)  # -1 to 1

    # Metrics
    estimated_reach = Column(Integer)
    social_shares = Column(Integer)

    # Timestamps
    published_at = Column(DateTime)
    discovered_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MediaMention {self.publication}: {self.title[:50]}...>"


class PROpportunity(Base):
    """PR opportunities based on media analysis"""
    __tablename__ = "pr_opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))

    # Opportunity details
    title = Column(String(255), nullable=False)
    description = Column(Text)
    publication = Column(String(255))

    # Relevance
    relevance_score = Column(Float)  # 0-100
    category = Column(String(100))  # 'tech', 'marketing', 'ecommerce', etc.

    # Contact info
    journalist_name = Column(String(255))
    journalist_email = Column(String(255))
    journalist_twitter = Column(String(100))

    # Status
    contacted = Column(Boolean, default=False)
    contacted_at = Column(DateTime)
    response_received = Column(Boolean, default=False)
    outcome = Column(String(50))  # 'coverage', 'declined', 'pending', etc.

    # Timestamps
    identified_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    def __repr__(self):
        return f"<PROpportunity {self.title} - {self.relevance_score}>"
