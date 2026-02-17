"""AI-generated strategy models"""
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from datetime import datetime
import enum
import uuid

from app.core.database import Base


class StrategyStatus(enum.Enum):
    """Strategy execution status"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class Strategy(Base):
    """90-day AI-generated strategic plans"""
    __tablename__ = "strategies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Strategy metadata
    name = Column(String(255), nullable=False)
    primary_goal = Column(Text, nullable=False)
    target_keywords = Column(ARRAY(String))
    target_regions = Column(ARRAY(String))  # Province/district codes

    # Timeline
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(Enum(StrategyStatus, name="strategystatus"), default=StrategyStatus.DRAFT, nullable=False)

    # Budget
    total_budget = Column(Float)  # TL
    budget_spent = Column(Float, default=0)

    # AI-generated content
    executive_summary = Column(Text)
    opportunities = Column(JSONB)  # Identified opportunities
    threats = Column(JSONB)  # Market threats/challenges
    kpi_targets = Column(JSONB)  # Target KPIs

    # Performance tracking
    current_kpis = Column(JSONB)  # Current KPI values
    completion_percentage = Column(Integer, default=0)

    # LLM metadata
    generated_by_model = Column(String(50))  # 'gpt-4o-mini', 'claude-haiku', etc.
    generation_timestamp = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="strategies")
    weeks = relationship("StrategyWeek", back_populates="strategy", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Strategy '{self.name}' ({self.status.value})>"


class StrategyWeek(Base):
    """Weekly breakdown of strategy"""
    __tablename__ = "strategy_weeks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False)

    week_number = Column(Integer, nullable=False)  # 1-13 for 90 days
    week_start_date = Column(DateTime, nullable=False)
    week_end_date = Column(DateTime, nullable=False)

    # Week objectives
    focus_area = Column(String(255))
    objectives = Column(JSONB)  # Weekly objectives
    budget_allocated = Column(Float)  # TL for this week

    # Progress
    completion_percentage = Column(Integer, default=0)
    notes = Column(Text)

    # Relationships
    strategy = relationship("Strategy", back_populates="weeks")
    tasks = relationship("StrategyTask", back_populates="week", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StrategyWeek {self.week_number} - {self.focus_area}>"


class TaskStatus(enum.Enum):
    """Task status"""
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class TaskPriority(enum.Enum):
    """Task priority"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class StrategyTask(Base):
    """Individual tasks within a strategy week"""
    __tablename__ = "strategy_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_id = Column(UUID(as_uuid=True), ForeignKey('strategy_weeks.id', ondelete='CASCADE'), nullable=False)

    # Task details
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # 'content', 'seo', 'ads', 'social', etc.

    # Metadata
    status = Column(Enum(TaskStatus, name="taskstatus"), default=TaskStatus.TODO, nullable=False)
    priority = Column(Enum(TaskPriority, name="taskpriority"), default=TaskPriority.MEDIUM, nullable=False)

    # Effort estimate
    estimated_hours = Column(Float)
    actual_hours = Column(Float)
    estimated_cost = Column(Float)  # TL

    # Assignment
    assigned_to = Column(String(255))  # Team member or role
    due_date = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    week = relationship("StrategyWeek", back_populates="tasks")

    def __repr__(self):
        return f"<StrategyTask '{self.title}' ({self.status.value})>"
