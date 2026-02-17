"""
AI endpoints for strategy generation and intelligent insights
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import logging

from app.services.strategy.generator import StrategyGenerator
from app.services.ai.chatbot import ChatbotService
from app.services.ai.agent import AgentService
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


# Request/Response models
class ChatRequest(BaseModel):
    """Request for AI chat"""
    message: str = Field(..., description="User message")
    history: List[Dict[str, str]] = Field(default_factory=list, description="Conversation history")

class ChatResponse(BaseModel):
    """Response from AI chat"""
    response: str

class StrategyGenerationRequest(BaseModel):
    """Request for AI strategy generation"""
    strategy_id: str = Field(..., description="Strategy ID")
    name: str = Field(..., description="Strategy name")
    primary_goal: str = Field(..., description="Primary business goal")
    target_keywords: List[str] = Field(..., description="Target keywords")
    target_regions: List[str] = Field(default_factory=list, description="Target regions")
    total_budget: float = Field(..., description="Total budget")


class StrategyGenerationResponse(BaseModel):
    """Response from AI strategy generation"""
    strategy_id: str
    executive_summary: str
    opportunities: Dict[str, Any]
    threats: Dict[str, Any]
    kpi_targets: Dict[str, Any]
    weeks: List[Dict[str, Any]]
    generation_model: str


class InsightRequest(BaseModel):
    """Request for AI insights"""
    context: str = Field(..., description="Context for insights")
    data: Dict[str, Any] = Field(..., description="Data to analyze")
    insight_type: str = Field(..., description="Type of insight: market, competitor, content")


class InsightResponse(BaseModel):
    """AI-generated insights"""
    insights: List[str]
    recommendations: List[str]
    confidence_score: float


@router.post("/strategy/generate", response_model=StrategyGenerationResponse)
async def generate_strategy(
    request: StrategyGenerationRequest,
    authorization: Optional[str] = Header(None)
) -> StrategyGenerationResponse:
    """
    Generate comprehensive 90-day strategy using AI

    This endpoint uses LLM (GPT-4 or Claude) to generate:
    - Executive summary
    - Opportunities and threats analysis
    - KPI targets
    - 12 weekly breakdowns with tasks
    """
    try:
        # Extract JWT token
        token = authorization.replace("Bearer ", "") if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization required")

        # Initialize strategy generator
        generator = StrategyGenerator()

        # Generate strategy with AI
        strategy_data = await generator.generate_comprehensive_strategy(
            name=request.name,
            primary_goal=request.primary_goal,
            target_keywords=request.target_keywords,
            target_regions=request.target_regions,
            total_budget=request.total_budget
        )

        return StrategyGenerationResponse(
            strategy_id=request.strategy_id,
            executive_summary=strategy_data["executive_summary"],
            opportunities=strategy_data["opportunities"],
            threats=strategy_data["threats"],
            kpi_targets=strategy_data["kpi_targets"],
            weeks=strategy_data["weeks"],
            generation_model=strategy_data.get("model", "claude-haiku")
        )

    except Exception as e:
        logger.error(f"Error generating strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
) -> ChatResponse:
    """
    Chat with STRATYON AI Assistant
    """
    try:
        # Optional: verify token if needed, or allow public chat for demo
        # token = authorization.replace("Bearer ", "") if authorization else None

        service = ChatbotService()
        response_text = await service.generate_response(request.message, request.history)

        return ChatResponse(response=response_text)

    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/chat", response_model=AgentChatResponse)
async def agent_chat(
    request: AgentChatRequest,
    authorization: Optional[str] = Header(None)
) -> AgentChatResponse:
    """
    Chat with STRATYON AI Agent

    This endpoint uses an intelligent agent that can:
    - Understand natural language commands
    - Navigate to pages
    - Select data
    - Execute actions across the platform

    Request includes context about current page, selected items, etc.
    Response includes conversational text, executable actions, and suggestions.
    """
    try:
        service = AgentService()
        result = await service.process_message(
            message=request.message,
            history=request.history,
            context=request.context
        )

        return AgentChatResponse(
            response=result.get("response", ""),
            actions=result.get("actions", []),
            suggestions=result.get("suggestions", [])
        )

    except Exception as e:
        logger.error(f"Error in agent chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights/generate", response_model=InsightResponse)
async def generate_insights(
    request: InsightRequest,
    authorization: Optional[str] = Header(None)
) -> InsightResponse:
    """
    Generate AI insights based on context and data

    Supports insight types:
    - market: Market analysis and trends
    - competitor: Competitor intelligence
    - content: Content recommendations
    """
    try:
        token = authorization.replace("Bearer ", "") if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization required")

        # TODO: Implement insight generation using LLM
        # This would analyze the provided data and generate actionable insights

        return InsightResponse(
            insights=[
                "Sample insight 1",
                "Sample insight 2"
            ],
            recommendations=[
                "Sample recommendation 1",
                "Sample recommendation 2"
            ],
            confidence_score=0.85
        )

    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/content/optimize")
async def optimize_content(
    content: str,
    target_keywords: List[str],
    content_type: str = "article",
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Optimize content for SEO and readability using AI
    """
    try:
        token = authorization.replace("Bearer ", "") if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization required")

        # TODO: Implement content optimization using LLM
        # Analyze content, suggest improvements, optimize for keywords

        return {
            "optimized_content": content,
            "seo_score": 85,
            "readability_score": 78,
            "suggestions": [
                "Add more relevant keywords",
                "Improve meta description"
            ]
        }

    except Exception as e:
        logger.error(f"Error optimizing content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaign/recommendations")
async def get_campaign_recommendations(
    business_goal: str,
    budget: float,
    target_audience: Dict[str, Any],
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Get AI-powered campaign recommendations
    """
    try:
        token = authorization.replace("Bearer ", "") if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization required")

        # TODO: Implement campaign recommendations using LLM
        # Analyze goal, budget, audience and recommend campaign structure

        return {
            "recommended_channels": ["Google Ads", "Meta Ads", "LinkedIn"],
            "budget_allocation": {
                "Google Ads": 0.5,
                "Meta Ads": 0.3,
                "LinkedIn": 0.2
            },
            "targeting_suggestions": [],
            "creative_recommendations": []
        }

    except Exception as e:
        logger.error(f"Error getting campaign recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
