"""User and authentication models"""
from sqlalchemy import Column, String, Boolean, Enum, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import enum
import uuid

from app.core.database import Base


class SubscriptionPlan(enum.Enum):
    """Subscription plan tiers"""
    FREE = "free"  # Limited features
    INSIGHT = "insight"  # ₺299/month - Basic GEOINT
    STRATEGY = "strategy"  # ₺599/month - + AI Strategy
    GROWTH = "growth"  # ₺999/month - + Competitor + Media
    ENTERPRISE = "enterprise"  # Custom pricing


class User(Base):
    """User accounts"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Profile
    full_name = Column(String(255))
    company_name = Column(String(255))
    phone = Column(String(20))

    # Subscription
    plan = Column(Enum(SubscriptionPlan, name="subscriptionplan", values_callable=lambda x: [e.value for e in x]), default=SubscriptionPlan.FREE, nullable=False)
    plan_started_at = Column(DateTime)
    plan_expires_at = Column(DateTime)

    # Limits based on plan
    max_keywords = Column(Integer, default=3)  # FREE: 3, INSIGHT: 10, STRATEGY: 50, GROWTH: 100
    max_competitors = Column(Integer, default=0)  # FREE: 0, GROWTH+: 20

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)

    # Relationships
    keywords = relationship("Keyword", back_populates="user", cascade="all, delete-orphan")
    competitors = relationship("Competitor", back_populates="user", cascade="all, delete-orphan")
    strategies = relationship("Strategy", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email} ({self.plan.value})>"
