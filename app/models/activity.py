"""Activity tracking model for dashboard"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import enum
import uuid

from app.core.database import Base


class ActivityType(enum.Enum):
    """Activity type enumeration"""
    KEYWORD_ADDED = "keyword_added"
    KEYWORD_DELETED = "keyword_deleted"
    STRATEGY_CREATED = "strategy_created"
    STRATEGY_UPDATED = "strategy_updated"
    COMPETITOR_ADDED = "competitor_added"
    COMPETITOR_ANALYZED = "competitor_analyzed"
    GEOINT_CALCULATED = "geoint_calculated"
    ALERT_TRIGGERED = "alert_triggered"


class Activity(Base):
    """User activity tracking for dashboard feed"""
    __tablename__ = "activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Activity details
    activity_type = Column(Enum(ActivityType, name="activitytype", values_callable=lambda x: [e.value for e in x]), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Optional reference to related entity
    entity_type = Column(String(50))  # 'keyword', 'strategy', 'competitor', etc.
    entity_id = Column(UUID(as_uuid=True))

    # Additional metadata
    # activity_metadata = Column("metadata", JSONB)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    user = relationship("User", back_populates="activities")

    def __repr__(self):
        return f"<Activity {self.activity_type.value}: {self.title}>"
