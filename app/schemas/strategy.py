"""Strategy-related schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from uuid import UUID


class StrategyStatusEnum(str, Enum):
    """Strategy status"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class TaskStatusEnum(str, Enum):
    """Task status"""
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class TaskPriorityEnum(str, Enum):
    """Task priority"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


# ============================================
# Request Schemas
# ============================================

class StrategyCreate(BaseModel):
    """Create strategy request"""
    name: str = Field(..., min_length=1, max_length=255)
    primary_goal: str = Field(..., min_length=1)
    target_keywords: List[str] = Field(default_factory=list)
    target_regions: List[str] = Field(default_factory=list)
    total_budget: Optional[float] = Field(None, gt=0)


class StrategyUpdate(BaseModel):
    """Update strategy request"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[StrategyStatusEnum] = None
    total_budget: Optional[float] = Field(None, gt=0)
    current_kpis: Optional[Dict] = None
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)


class TaskCreate(BaseModel):
    """Create task request"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    priority: TaskPriorityEnum = TaskPriorityEnum.MEDIUM
    estimated_hours: Optional[float] = Field(None, gt=0)
    estimated_cost: Optional[float] = Field(None, gt=0)
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    """Update task request"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatusEnum] = None
    priority: Optional[TaskPriorityEnum] = None
    actual_hours: Optional[float] = Field(None, gt=0)
    completed_at: Optional[datetime] = None


# ============================================
# Response Schemas
# ============================================

class TaskResponse(BaseModel):
    """Task response"""
    id: UUID
    week_id: UUID
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    status: str
    priority: str
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WeekResponse(BaseModel):
    """Strategy week response"""
    id: UUID
    strategy_id: UUID
    week_number: int
    week_start_date: datetime
    week_end_date: datetime
    focus_area: Optional[str] = None
    objectives: Optional[List[str]] = None
    budget_allocated: Optional[float] = None
    completion_percentage: int
    notes: Optional[str] = None
    tasks: List[TaskResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class StrategyResponse(BaseModel):
    """Strategy response"""
    id: UUID
    user_id: UUID
    name: str
    primary_goal: str
    target_keywords: List[str]
    target_regions: List[str]
    start_date: datetime
    end_date: datetime
    status: str
    total_budget: Optional[float] = None
    budget_spent: float
    executive_summary: Optional[str] = None
    opportunities: Optional[List[Dict]] = None
    threats: Optional[List[Dict]] = None
    kpi_targets: Optional[Dict] = None
    current_kpis: Optional[Dict] = None
    completion_percentage: int
    generated_by_model: Optional[str] = None
    generation_timestamp: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StrategyWithWeeks(StrategyResponse):
    """Strategy with weekly breakdown"""
    weeks: List[WeekResponse] = Field(default_factory=list)


class StrategyGenerationRequest(BaseModel):
    """AI strategy generation request"""
    name: str
    primary_goal: str
    target_keywords: List[str] = Field(default_factory=list)
    total_budget: Optional[float] = None
    industry: Optional[str] = None
    target_audience: Optional[str] = None


# ============================================
# AI Generation & Refinement Schemas
# ============================================

class StrategyGenerateForExistingRequest(BaseModel):
    """Generate AI content for existing draft strategy"""
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    regenerate: bool = Field(default=False, description="If true, regenerate even if AI content exists")


class AIRefinementRequest(BaseModel):
    """Request AI refinement suggestions"""
    action: str = Field(..., description="Type of refinement: 'analyze_progress', 'suggest_improvements', 'adjust_timeline'")
    context: Optional[str] = Field(None, description="Additional context for the AI")
    specific_week: Optional[int] = Field(None, description="Focus on specific week (1-13)")


class AIRefinementResponse(BaseModel):
    """AI refinement response"""
    action: str
    suggestions: List[Dict]
    summary: str
    confidence_score: float = Field(ge=0, le=1)
    generated_by: str


# ============================================
# Progress Tracking Schemas
# ============================================

class TaskProgressSummary(BaseModel):
    """Summary of task progress"""
    total: int
    completed: int
    in_progress: int
    todo: int
    blocked: int
    completion_rate: float


class WeekProgressSummary(BaseModel):
    """Summary of week progress"""
    week_number: int
    focus_area: Optional[str]
    completion_percentage: int
    budget_allocated: Optional[float]
    budget_spent: Optional[float]
    tasks: TaskProgressSummary


class KPIMetric(BaseModel):
    """KPI metric with target and current value"""
    name: str
    target: Optional[str]
    current: Optional[str]
    progress_percentage: Optional[float]
    trend: Optional[str]  # 'up', 'down', 'stable'


class StrategyProgressResponse(BaseModel):
    """Complete progress metrics for a strategy"""
    strategy_id: UUID
    overall_completion: int
    budget_total: Optional[float]
    budget_spent: float
    budget_remaining: Optional[float]
    days_elapsed: int
    days_remaining: int
    current_week: int
    total_weeks: int
    weeks_summary: List[WeekProgressSummary]
    kpi_metrics: List[KPIMetric]
    tasks_summary: TaskProgressSummary
    is_on_track: bool
    ai_generated: bool
