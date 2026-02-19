"""
Strategy API Endpoints

Provides endpoints for:
- Strategy CRUD operations
- AI-powered strategy generation
- Weekly task management
- KPI tracking and progress monitoring
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from typing import Dict,  List, Optional
import logging
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.strategy import Strategy, StrategyWeek, StrategyTask
from app.schemas.strategy import (
    StrategyCreate,
    StrategyUpdate,
    StrategyResponse,
    StrategyWithWeeks,
    StrategyGenerationRequest,
    StrategyGenerateForExistingRequest,
    AIRefinementRequest,
    AIRefinementResponse,
    StrategyProgressResponse,
    WeekProgressSummary,
    TaskProgressSummary,
    KPIMetric,
    WeekResponse,
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskStatusEnum,
)
from app.services.strategy.generator import StrategyGenerator

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# Helper Functions to avoid lazy loading issues
# ============================================

def build_strategy_response(strategy: Strategy) -> StrategyResponse:
    """Build StrategyResponse manually to avoid lazy loading"""
    return StrategyResponse(
        id=strategy.id,
        user_id=strategy.user_id,
        name=strategy.name,
        primary_goal=strategy.primary_goal,
        target_keywords=strategy.target_keywords or [],
        target_regions=strategy.target_regions or [],
        start_date=strategy.start_date,
        end_date=strategy.end_date,
        status=strategy.status.value if hasattr(strategy.status, 'value') else str(strategy.status),
        total_budget=strategy.total_budget,
        budget_spent=strategy.budget_spent or 0,
        executive_summary=strategy.executive_summary,
        opportunities=strategy.opportunities,
        threats=strategy.threats,
        kpi_targets=strategy.kpi_targets,
        current_kpis=strategy.current_kpis,
        completion_percentage=strategy.completion_percentage or 0,
        generated_by_model=strategy.generated_by_model,
        generation_timestamp=strategy.generation_timestamp,
        created_at=strategy.created_at,
        updated_at=strategy.updated_at
    )


def build_strategy_with_weeks(strategy: Strategy, weeks_data: List[WeekResponse]) -> StrategyWithWeeks:
    """Build StrategyWithWeeks manually to avoid lazy loading"""
    return StrategyWithWeeks(
        id=strategy.id,
        user_id=strategy.user_id,
        name=strategy.name,
        primary_goal=strategy.primary_goal,
        target_keywords=strategy.target_keywords or [],
        target_regions=strategy.target_regions or [],
        start_date=strategy.start_date,
        end_date=strategy.end_date,
        status=strategy.status.value if hasattr(strategy.status, 'value') else str(strategy.status),
        total_budget=strategy.total_budget,
        budget_spent=strategy.budget_spent or 0,
        executive_summary=strategy.executive_summary,
        opportunities=strategy.opportunities,
        threats=strategy.threats,
        kpi_targets=strategy.kpi_targets,
        current_kpis=strategy.current_kpis,
        completion_percentage=strategy.completion_percentage or 0,
        generated_by_model=strategy.generated_by_model,
        generation_timestamp=strategy.generation_timestamp,
        created_at=strategy.created_at,
        updated_at=strategy.updated_at,
        weeks=weeks_data
    )


# ============================================
# Strategy Endpoints
# ============================================

@router.post("/generate", response_model=StrategyWithWeeks, status_code=status.HTTP_201_CREATED)
async def generate_strategy(
    request: StrategyGenerationRequest,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a complete 90-day AI-powered strategy

    Uses OpenAI GPT-4o-mini or Anthropic Claude to generate:
    - Executive summary
    - SWOT analysis
    - 90-day weekly breakdown
    - Actionable tasks with deadlines
    - Budget allocation
    - KPI targets
    """
    try:
        logger.info(f"🤖 Generating strategy for user {current_user.get('id')}: {request.name}")

        generator = StrategyGenerator(db)
        strategy = await generator.generate_strategy(
            user_id=str(current_user.get('id')),
            name=request.name,
            primary_goal=request.primary_goal,
            target_keywords=request.target_keywords,
            total_budget=request.total_budget,
            industry=request.industry,
            target_audience=request.target_audience,
        )

        # Fetch strategy with weeks
        result = await db.execute(
            select(Strategy)
            .where(Strategy.id == strategy.id)
        )
        strategy_obj = result.scalar_one()

        # Load weeks and tasks
        weeks_result = await db.execute(
            select(StrategyWeek)
            .where(StrategyWeek.strategy_id == strategy.id)
            .order_by(StrategyWeek.week_number)
        )
        weeks = weeks_result.scalars().all()

        # Load tasks for each week
        weeks_data = []
        for week in weeks:
            tasks_result = await db.execute(
                select(StrategyTask)
                .where(StrategyTask.week_id == week.id)
                .order_by(StrategyTask.id)
            )
            tasks = tasks_result.scalars().all()

            # Calculate completion percentage from actual tasks
            completed_count = sum(1 for t in tasks if t.status.value == "COMPLETED")
            total_count = len(tasks)
            calculated_completion = round((completed_count / total_count) * 100) if total_count > 0 else 0

            # Build week dict manually to avoid lazy loading issues
            week_data = WeekResponse(
                id=week.id,
                strategy_id=week.strategy_id,
                week_number=week.week_number,
                week_start_date=week.week_start_date,
                week_end_date=week.week_end_date,
                focus_area=week.focus_area,
                objectives=week.objectives,
                budget_allocated=week.budget_allocated,
                completion_percentage=calculated_completion,
                notes=week.notes,
                tasks=[TaskResponse.model_validate(t) for t in tasks]
            )
            weeks_data.append(week_data)

        response = build_strategy_with_weeks(strategy_obj, weeks_data)

        logger.info(f"✅ Strategy generated with {len(weeks_data)} weeks")
        return response

    except Exception as e:
        logger.error(f"❌ Error generating strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate strategy: {str(e)}"
        )


@router.get("/", response_model=List[StrategyResponse])
async def list_strategies(
    skip: int = 0,
    limit: int = 20,
    status_filter: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all strategies for the current user

    Filters:
    - status: draft, active, paused, completed, archived
    """
    try:
        from sqlalchemy import func, Integer
        from app.models.strategy import TaskStatus

        logger.info(f"📥 GET /strategies - user_id: {current_user.get('id')}, skip: {skip}, limit: {limit}, status: {status_filter}")
        query = select(Strategy).where(Strategy.user_id == current_user.get('id'))

        if status_filter:
            query = query.where(Strategy.status == status_filter)

        query = query.order_by(Strategy.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        strategies = result.scalars().all()

        # Calculate completion for each strategy from actual task data
        strategy_responses = []
        for strategy in strategies:
            # Get task counts for this strategy
            tasks_result = await db.execute(
                select(
                    func.count(StrategyTask.id).label("total"),
                    func.sum(
                        func.cast(StrategyTask.status == TaskStatus.COMPLETED, type_=Integer)
                    ).label("completed")
                ).join(
                    StrategyWeek, StrategyTask.week_id == StrategyWeek.id
                ).where(StrategyWeek.strategy_id == strategy.id)
            )
            tasks_row = tasks_result.fetchone()

            total_tasks = int(tasks_row.total or 0) if tasks_row else 0
            completed_tasks = int(tasks_row.completed or 0) if tasks_row else 0
            calculated_completion = round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

            # Build response with calculated completion
            response = StrategyResponse(
                id=strategy.id,
                user_id=strategy.user_id,
                name=strategy.name,
                primary_goal=strategy.primary_goal,
                target_keywords=strategy.target_keywords or [],
                target_regions=strategy.target_regions or [],
                start_date=strategy.start_date,
                end_date=strategy.end_date,
                status=strategy.status.value if hasattr(strategy.status, 'value') else str(strategy.status),
                total_budget=strategy.total_budget,
                budget_spent=strategy.budget_spent or 0,
                executive_summary=strategy.executive_summary,
                opportunities=strategy.opportunities,
                threats=strategy.threats,
                kpi_targets=strategy.kpi_targets,
                current_kpis=strategy.current_kpis,
                completion_percentage=calculated_completion,  # Use calculated value
                generated_by_model=strategy.generated_by_model,
                generation_timestamp=strategy.generation_timestamp,
                created_at=strategy.created_at,
                updated_at=strategy.updated_at
            )
            strategy_responses.append(response)

        logger.info(f"📤 GET /strategies - returning {len(strategy_responses)} strategies")
        return strategy_responses

    except Exception as e:
        logger.error(f"❌ Error listing strategies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list strategies"
        )


@router.get("/{strategy_id}", response_model=StrategyWithWeeks)
async def get_strategy(
    strategy_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single strategy with all weeks and tasks
    """
    try:
        logger.info(f"📥 GET /strategies/{strategy_id} - user_id: {current_user.get('id')}")
        # Fetch strategy
        result = await db.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == current_user.get('id')
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        # Load weeks
        weeks_result = await db.execute(
            select(StrategyWeek)
            .where(StrategyWeek.strategy_id == strategy_id)
            .order_by(StrategyWeek.week_number)
        )
        weeks = weeks_result.scalars().all()

        # Load tasks for each week
        weeks_data = []
        for week in weeks:
            tasks_result = await db.execute(
                select(StrategyTask)
                .where(StrategyTask.week_id == week.id)
                .order_by(StrategyTask.id)
            )
            tasks = tasks_result.scalars().all()

            # Calculate completion percentage from actual tasks (not stale DB value)
            completed_count = sum(1 for t in tasks if t.status.value == "COMPLETED")
            total_count = len(tasks)
            calculated_completion = round((completed_count / total_count) * 100) if total_count > 0 else 0

            # Build week dict manually to avoid lazy loading issues
            week_data = WeekResponse(
                id=week.id,
                strategy_id=week.strategy_id,
                week_number=week.week_number,
                week_start_date=week.week_start_date,
                week_end_date=week.week_end_date,
                focus_area=week.focus_area,
                objectives=week.objectives,
                budget_allocated=week.budget_allocated,
                completion_percentage=calculated_completion,
                notes=week.notes,
                tasks=[TaskResponse.model_validate(t) for t in tasks]
            )
            weeks_data.append(week_data)

        response = build_strategy_with_weeks(strategy, weeks_data)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get strategy"
        )


@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_data: StrategyCreate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a manual strategy (without AI generation)
    """
    try:
        from datetime import timedelta

        from app.models.strategy import StrategyStatus

        strategy = Strategy(
            user_id=str(current_user.get('id')),
            name=strategy_data.name,
            primary_goal=strategy_data.primary_goal,
            target_keywords=strategy_data.target_keywords,
            target_regions=strategy_data.target_regions,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=90),
            total_budget=strategy_data.total_budget,
            status=StrategyStatus.DRAFT
        )

        db.add(strategy)
        await db.commit()
        await db.refresh(strategy)

        logger.info(f"✅ Created manual strategy {strategy.id}")
        return build_strategy_response(strategy)

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error creating strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create strategy"
        )


@router.patch("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: str,
    strategy_data: StrategyUpdate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a strategy
    """
    try:
        # Verify ownership
        result = await db.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == current_user.get('id')
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        # Update fields
        update_data = strategy_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(strategy, field, value)

        strategy.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(strategy)

        logger.info(f"✅ Updated strategy {strategy_id}")
        return build_strategy_response(strategy)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error updating strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update strategy"
        )


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a strategy (cascade deletes weeks and tasks)
    """
    try:
        # Verify ownership
        result = await db.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == current_user.get('id')
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        await db.delete(strategy)
        await db.commit()

        logger.info(f"✅ Deleted strategy {strategy_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error deleting strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete strategy"
        )


# ============================================
# Task Endpoints
# ============================================

@router.post("/{strategy_id}/weeks/{week_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    strategy_id: str,
    week_id: str,
    task_data: TaskCreate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new task for a specific week
    """
    try:
        # Verify strategy ownership and week exists
        result = await db.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == current_user.get('id')
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        # Verify week exists
        week_result = await db.execute(
            select(StrategyWeek).where(
                and_(
                    StrategyWeek.id == week_id,
                    StrategyWeek.strategy_id == strategy_id
                )
            )
        )
        week = week_result.scalar_one_or_none()

        if not week:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Week not found"
            )

        # Create task
        task = StrategyTask(
            week_id=week_id,
            **task_data.model_dump()
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        logger.info(f"✅ Created task {task.id} for week {week_id}")
        return TaskResponse.model_validate(task)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error creating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a task
    """
    try:
        # Get task and verify ownership through strategy
        result = await db.execute(
            select(StrategyTask)
            .join(StrategyWeek, StrategyTask.week_id == StrategyWeek.id)
            .join(Strategy, StrategyWeek.strategy_id == Strategy.id)
            .where(
                and_(
                    StrategyTask.id == task_id,
                    Strategy.user_id == current_user.get('id')
                )
            )
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Update fields
        update_data = task_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        # Auto-set completed_at if status is completed
        from app.schemas.strategy import TaskStatusEnum
        if task_data.status == TaskStatusEnum.COMPLETED and not task.completed_at:
            task.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(task)

        logger.info(f"✅ Updated task {task_id}")
        return TaskResponse.model_validate(task)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error updating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a task
    """
    try:
        # Get task and verify ownership
        result = await db.execute(
            select(StrategyTask)
            .join(StrategyWeek, StrategyTask.week_id == StrategyWeek.id)
            .join(Strategy, StrategyWeek.strategy_id == Strategy.id)
            .where(
                and_(
                    StrategyTask.id == task_id,
                    Strategy.user_id == current_user.get('id')
                )
            )
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        await db.delete(task)
        await db.commit()

        logger.info(f"✅ Deleted task {task_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error deleting task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )


# ============================================
# AI Generation & Refinement Endpoints
# ============================================

@router.post("/{strategy_id}/generate", response_model=StrategyWithWeeks)
async def generate_ai_for_existing_strategy(
    strategy_id: str,
    request: StrategyGenerateForExistingRequest,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI content for an existing draft strategy

    This endpoint allows users to:
    1. Create a draft strategy first (via POST /strategies/)
    2. Later trigger AI generation for that draft

    Returns the strategy with AI-generated weeks and tasks.
    """
    try:
        logger.info(f"🤖 Generating AI content for strategy {strategy_id}")

        # Fetch strategy
        result = await db.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == current_user.get('id')
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        # Check if already has AI content
        if strategy.generated_by_model and not request.regenerate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Strategy already has AI-generated content. Set regenerate=true to regenerate."
            )

        # If regenerating, delete existing weeks and tasks
        if request.regenerate:
            await db.execute(
                delete(StrategyWeek).where(StrategyWeek.strategy_id == strategy_id)
            )
            await db.flush()

        # Generate AI content
        generator = StrategyGenerator(db)
        strategy_content = await generator._generate_with_llm(
            primary_goal=strategy.primary_goal,
            context=await generator._gather_context(
                str(current_user.get('id')),
                strategy.target_keywords or []
            ),
            budget=strategy.total_budget,
            industry=request.industry,
            target_audience=request.target_audience
        )

        # Update strategy with AI content
        strategy.executive_summary = strategy_content.get("executive_summary")
        strategy.opportunities = strategy_content.get("opportunities")
        strategy.threats = strategy_content.get("threats")
        strategy.kpi_targets = strategy_content.get("kpi_targets")
        strategy.generated_by_model = strategy_content.get("model")
        strategy.generation_timestamp = datetime.utcnow()

        # Create weekly plan
        await generator._create_weekly_plan(strategy, strategy_content.get("weeks", []))

        await db.commit()
        await db.refresh(strategy)

        # Fetch with weeks for response
        weeks_result = await db.execute(
            select(StrategyWeek)
            .where(StrategyWeek.strategy_id == strategy_id)
            .order_by(StrategyWeek.week_number)
        )
        weeks = weeks_result.scalars().all()

        weeks_data = []
        for week in weeks:
            tasks_result = await db.execute(
                select(StrategyTask)
                .where(StrategyTask.week_id == week.id)
                .order_by(StrategyTask.id)
            )
            tasks = tasks_result.scalars().all()

            # Calculate completion percentage from actual tasks
            completed_count = sum(1 for t in tasks if t.status.value == "COMPLETED")
            total_count = len(tasks)
            calculated_completion = round((completed_count / total_count) * 100) if total_count > 0 else 0

            # Build week dict manually to avoid lazy loading issues
            week_data = WeekResponse(
                id=week.id,
                strategy_id=week.strategy_id,
                week_number=week.week_number,
                week_start_date=week.week_start_date,
                week_end_date=week.week_end_date,
                focus_area=week.focus_area,
                objectives=week.objectives,
                budget_allocated=week.budget_allocated,
                completion_percentage=calculated_completion,
                notes=week.notes,
                tasks=[TaskResponse.model_validate(t) for t in tasks]
            )
            weeks_data.append(week_data)

        response = build_strategy_with_weeks(strategy, weeks_data)

        logger.info(f"✅ AI content generated for strategy {strategy_id} with {len(weeks_data)} weeks")
        return response

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error generating AI content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI content: {str(e)}"
        )


@router.get("/{strategy_id}/weeks", response_model=List[WeekResponse])
async def get_strategy_weeks(
    strategy_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all weeks with tasks for a strategy
    """
    try:
        # Verify ownership
        result = await db.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == current_user.get('id')
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        # Fetch weeks
        weeks_result = await db.execute(
            select(StrategyWeek)
            .where(StrategyWeek.strategy_id == strategy_id)
            .order_by(StrategyWeek.week_number)
        )
        weeks = weeks_result.scalars().all()

        # Load tasks for each week
        weeks_data = []
        for week in weeks:
            tasks_result = await db.execute(
                select(StrategyTask)
                .where(StrategyTask.week_id == week.id)
                .order_by(StrategyTask.id)
            )
            tasks = tasks_result.scalars().all()

            # Calculate completion percentage from actual tasks (not stale DB value)
            completed_count = sum(1 for t in tasks if t.status.value == "COMPLETED")
            total_count = len(tasks)
            calculated_completion = round((completed_count / total_count) * 100) if total_count > 0 else 0

            # Build week dict manually to avoid lazy loading issues
            week_data = WeekResponse(
                id=week.id,
                strategy_id=week.strategy_id,
                week_number=week.week_number,
                week_start_date=week.week_start_date,
                week_end_date=week.week_end_date,
                focus_area=week.focus_area,
                objectives=week.objectives,
                budget_allocated=week.budget_allocated,
                completion_percentage=calculated_completion,
                notes=week.notes,
                tasks=[TaskResponse.model_validate(t) for t in tasks]
            )
            weeks_data.append(week_data)

        return weeks_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching weeks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch weeks"
        )


@router.get("/{strategy_id}/progress", response_model=StrategyProgressResponse)
async def get_strategy_progress(
    strategy_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive progress metrics for a strategy

    Returns:
    - Overall completion percentage
    - Budget metrics (total, spent, remaining)
    - Timeline metrics (days elapsed, remaining, current week)
    - Week-by-week progress summary
    - KPI metrics
    - Task summary
    """
    try:
        # Fetch strategy
        result = await db.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == current_user.get('id')
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        # Fetch all weeks with tasks
        weeks_result = await db.execute(
            select(StrategyWeek)
            .where(StrategyWeek.strategy_id == strategy_id)
            .order_by(StrategyWeek.week_number)
        )
        weeks = weeks_result.scalars().all()

        # Calculate metrics
        now = datetime.utcnow()
        days_elapsed = max(0, (now - strategy.start_date).days)
        days_remaining = max(0, (strategy.end_date - now).days)
        current_week = min(13, max(1, (days_elapsed // 7) + 1))

        # Task summary across all weeks
        total_tasks = 0
        completed_tasks = 0
        in_progress_tasks = 0
        todo_tasks = 0
        blocked_tasks = 0
        total_budget_spent = 0  # Calculate from completed task costs

        weeks_summary = []
        for week in weeks:
            tasks_result = await db.execute(
                select(StrategyTask)
                .where(StrategyTask.week_id == week.id)
            )
            tasks = tasks_result.scalars().all()

            week_completed = sum(1 for t in tasks if t.status.value == "COMPLETED")
            week_in_progress = sum(1 for t in tasks if t.status.value == "IN_PROGRESS")
            week_todo = sum(1 for t in tasks if t.status.value == "TODO")
            week_blocked = sum(1 for t in tasks if t.status.value == "BLOCKED")
            week_total = len(tasks)

            # Calculate budget spent from completed tasks' estimated_cost
            week_budget_spent = sum(
                t.estimated_cost or 0
                for t in tasks
                if t.status.value == "COMPLETED" and t.estimated_cost
            )

            total_tasks += week_total
            completed_tasks += week_completed
            in_progress_tasks += week_in_progress
            todo_tasks += week_todo
            blocked_tasks += week_blocked
            total_budget_spent += week_budget_spent

            # Calculate week completion from actual tasks (not stale DB value)
            week_completion_pct = round(week_completed / week_total * 100) if week_total > 0 else 0

            weeks_summary.append(WeekProgressSummary(
                week_number=week.week_number,
                focus_area=week.focus_area,
                completion_percentage=week_completion_pct,
                budget_allocated=week.budget_allocated,
                budget_spent=week_budget_spent,
                tasks=TaskProgressSummary(
                    total=week_total,
                    completed=week_completed,
                    in_progress=week_in_progress,
                    todo=week_todo,
                    blocked=week_blocked,
                    completion_rate=round(week_completed / week_total * 100, 1) if week_total > 0 else 0
                )
            ))

        # Calculate overall completion from actual task data (not stale DB value)
        overall_completion_pct = round(completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Calculate KPI metrics from targets with estimated progress
        kpi_metrics = []
        if strategy.kpi_targets:
            for key, target in strategy.kpi_targets.items():
                current_value = strategy.current_kpis.get(key) if strategy.current_kpis else None
                # If no current value stored, estimate based on completion rate
                estimated_current = None
                progress_pct = None
                trend = None

                if target and not current_value:
                    # Parse target value and estimate current based on completion
                    try:
                        target_str = str(target).replace('%', '').replace(',', '.')
                        target_num = float(target_str)
                        estimated_num = target_num * (overall_completion_pct / 100)
                        estimated_current = f"{estimated_num:.1f}%"
                        progress_pct = overall_completion_pct
                        trend = 'up' if overall_completion_pct > 25 else 'stable'
                    except (ValueError, TypeError):
                        estimated_current = None

                kpi_metrics.append(KPIMetric(
                    name=key.replace("_", " ").title(),
                    target=str(target) if target else None,
                    current=str(current_value) if current_value else estimated_current,
                    progress_percentage=progress_pct,
                    trend=trend
                ))

        # Determine if on track (simple heuristic)
        expected_completion = (days_elapsed / 90) * 100 if days_elapsed <= 90 else 100
        is_on_track = overall_completion_pct >= (expected_completion * 0.8)

        # Use calculated budget_spent from completed tasks
        actual_budget_spent = total_budget_spent if total_budget_spent > 0 else (strategy.budget_spent or 0)

        return StrategyProgressResponse(
            strategy_id=strategy.id,
            overall_completion=overall_completion_pct,
            budget_total=strategy.total_budget,
            budget_spent=actual_budget_spent,
            budget_remaining=strategy.total_budget - actual_budget_spent if strategy.total_budget else None,
            days_elapsed=days_elapsed,
            days_remaining=days_remaining,
            current_week=current_week,
            total_weeks=len(weeks),
            weeks_summary=weeks_summary,
            kpi_metrics=kpi_metrics,
            tasks_summary=TaskProgressSummary(
                total=total_tasks,
                completed=completed_tasks,
                in_progress=in_progress_tasks,
                todo=todo_tasks,
                blocked=blocked_tasks,
                completion_rate=round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0
            ),
            is_on_track=is_on_track,
            ai_generated=strategy.generated_by_model is not None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get progress"
        )


@router.post("/{strategy_id}/refine", response_model=AIRefinementResponse)
async def refine_strategy(
    strategy_id: str,
    request: AIRefinementRequest,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-powered refinement suggestions for a strategy

    Actions:
    - analyze_progress: Analyze current progress and identify issues
    - suggest_improvements: Get improvement recommendations
    - adjust_timeline: Get timeline adjustment suggestions
    """
    try:
        from app.services.strategy.refiner import StrategyRefiner

        # Verify ownership
        result = await db.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == current_user.get('id')
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        refiner = StrategyRefiner(db)

        if request.action == "analyze_progress":
            result = await refiner.analyze_progress(strategy_id)
        elif request.action == "suggest_improvements":
            result = await refiner.suggest_improvements(
                strategy_id,
                context=request.context,
                specific_week=request.specific_week
            )
        elif request.action == "adjust_timeline":
            result = await refiner.adjust_timeline(
                strategy_id,
                reason=request.context
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown action: {request.action}"
            )

        return AIRefinementResponse(
            action=request.action,
            suggestions=result.get("suggestions", []),
            summary=result.get("summary", ""),
            confidence_score=result.get("confidence_score", 0.7),
            generated_by=result.get("model", "template")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error refining strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refine strategy: {str(e)}"
        )
