"""
Competitor Intelligence API Endpoints

Provides endpoints for:
- Competitor tracking and monitoring
- Domain metrics analysis
- Keyword overlap and gap analysis
- Historical trend tracking
- AI-powered competitor insights
- Backlink profile analysis
- Side-by-side comparison
- Market overview
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, desc
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.competitor import Competitor, CompetitorSnapshot
from app.schemas.competitor import (
    CompetitorCreate,
    CompetitorUpdate,
    CompetitorResponse,
    CompetitorWithSnapshots,
    CompetitorAnalyzeRequest,
    CompetitorSnapshotResponse,
    CompetitorKeywordOverlap,
    CompetitorGapAnalysis,
    CompetitorCompareRequest,
    AIInsightsRequest,
    CompetitorTrendsResponse,
    BacklinkProfileResponse,
    ContentGapResponse,
    AdIntelligenceResponse,
    TechStackResponse,
    MarketOverviewResponse,
    CompetitorComparisonResponse,
    CompetitorInsights,
)
from app.services.external.dataforseo import DataForSEOClient
from app.services.competitor_analysis import CompetitorAnalysisService

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# Helper Functions
# ============================================

async def analyze_competitor_domain(competitor_id: str):
    """
    Background task to analyze competitor domain metrics.
    Creates its own database session since the request session is closed.
    """
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"🔄 Starting analysis for competitor {competitor_id}")

            result = await db.execute(
                select(Competitor).where(Competitor.id == competitor_id)
            )
            competitor = result.scalar_one_or_none()

            if not competitor:
                logger.error(f"Competitor {competitor_id} not found")
                return

            logger.info(f"📊 Fetching metrics for {competitor.domain}...")

            # Use DataForSEO to get domain metrics
            async with DataForSEOClient() as dataforseo:
                # Get domain metrics
                domain_metrics = await dataforseo.get_domain_metrics(competitor.domain)

                logger.info(f"📊 Domain metrics received: {domain_metrics}")

                if domain_metrics:
                    competitor.domain_authority = domain_metrics.get("domain_rank") or 0
                    competitor.organic_traffic = domain_metrics.get("organic_etv") or 0
                    competitor.organic_keywords = domain_metrics.get("organic_keywords_count") or 0
                    competitor.total_backlinks = domain_metrics.get("backlinks") or 0
                    competitor.referring_domains = domain_metrics.get("referring_domains") or 0

                # Get competitor keywords
                keywords = await dataforseo.get_competitor_keywords(
                    competitor.domain,
                    limit=100
                ) or []  # Ensure list even if None returned

            competitor.paid_keywords = len([k for k in keywords if k.get("is_paid")])

            # Create snapshot
            snapshot = CompetitorSnapshot(
                competitor_id=competitor.id,
                domain_authority=competitor.domain_authority,
                organic_traffic=competitor.organic_traffic,
                organic_keywords=competitor.organic_keywords,
                total_backlinks=competitor.total_backlinks,
                referring_domains=competitor.referring_domains,
                top_keywords=[
                    {
                        "keyword": k.get("keyword"),
                        "position": k.get("position"),
                        "search_volume": k.get("search_volume"),
                        "url": k.get("url"),
                    }
                    for k in keywords[:20]  # Top 20 keywords
                ],
                snapshot_date=datetime.utcnow()
            )

            db.add(snapshot)
            competitor.last_analyzed_at = datetime.utcnow()
            competitor.updated_at = datetime.utcnow()

            await db.commit()

            logger.info(f"✅ Analyzed competitor {competitor.domain}: DA={competitor.domain_authority}, Traffic={competitor.organic_traffic}, Keywords={competitor.organic_keywords}")

        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Error analyzing competitor {competitor_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())


# ============================================
# Static Path Endpoints (MUST come before /{competitor_id})
# ============================================

@router.get("/market-overview", response_model=MarketOverviewResponse)
async def get_market_overview(
    user_domain: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get market overview with industry benchmarks

    Analyzes all tracked competitors to provide market insights.
    """
    try:
        logger.info(f"📥 GET /competitors/market-overview")

        service = CompetitorAnalysisService(db)
        try:
            overview = await service.get_market_overview(
                UUID(current_user.get('id')),
                user_domain
            )
            return overview
        finally:
            await service.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting market overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get market overview"
        )


@router.post("/compare", response_model=CompetitorComparisonResponse)
async def compare_competitors(
    request: CompetitorCompareRequest,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare 2-4 competitors side-by-side

    Returns metrics comparison, rankings, and radar chart data.
    """
    try:
        logger.info(f"📥 POST /competitors/compare - user_id: {current_user.get('id')}")

        # Verify all competitors belong to user
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id.in_(request.competitor_ids),
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitors = result.scalars().all()

        if len(competitors) != len(request.competitor_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more competitors not found"
            )

        service = CompetitorAnalysisService(db)
        try:
            comparison = await service.compare_competitors(
                request.competitor_ids,
                request.user_domain
            )
            return comparison
        finally:
            await service.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error comparing competitors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare competitors"
        )


# ============================================
# Competitor CRUD Endpoints
# ============================================

@router.get("", response_model=List[CompetitorResponse])
async def list_competitors(
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all tracked competitors for the current user
    """
    try:
        logger.info(f"📥 GET /competitors - user_id: {current_user.get('id')}, skip: {skip}, limit: {limit}, category: {category}")
        query = select(Competitor).where(Competitor.user_id == current_user.get('id'))

        if category:
            query = query.where(Competitor.category == category)

        query = query.order_by(Competitor.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        competitors = result.scalars().all()

        logger.info(f"📤 GET /competitors - returning {len(competitors)} competitors")
        return [CompetitorResponse.model_validate(c) for c in competitors]

    except Exception as e:
        logger.error(f"❌ Error listing competitors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list competitors"
        )


@router.post("", response_model=CompetitorResponse, status_code=status.HTTP_201_CREATED)
async def create_competitor(
    competitor_data: CompetitorCreate,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new competitor to track

    Automatically triggers background analysis to fetch initial metrics.
    """
    try:
        # Check if competitor already exists for this user
        existing = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.user_id == current_user.get('id'),
                    Competitor.domain == competitor_data.domain
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competitor domain already tracked"
            )

        # Create competitor
        competitor = Competitor(
            user_id=current_user.get('id'),
            **competitor_data.model_dump()
        )

        db.add(competitor)
        await db.commit()
        await db.refresh(competitor)

        # Trigger background analysis
        background_tasks.add_task(analyze_competitor_domain, str(competitor.id))

        logger.info(f"✅ Created competitor {competitor.domain} for user {current_user.get('id')}")
        return CompetitorResponse.model_validate(competitor)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error creating competitor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create competitor"
        )


@router.get("/{competitor_id}", response_model=CompetitorWithSnapshots)
async def get_competitor(
    competitor_id: str,
    include_snapshots: bool = True,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single competitor with optional historical snapshots
    """
    try:
        logger.info(f"📥 GET /competitors/{competitor_id} - user_id: {current_user.get('id')}, include_snapshots: {include_snapshots}")
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id == competitor_id,
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found"
            )

        # Build base response dict from competitor (avoids lazy loading issues)
        competitor_dict = {
            "id": competitor.id,
            "user_id": competitor.user_id,
            "domain": competitor.domain,
            "name": competitor.name,
            "category": competitor.category,
            "domain_authority": competitor.domain_authority,
            "page_authority": competitor.page_authority,
            "trust_flow": competitor.trust_flow,
            "citation_flow": competitor.citation_flow,
            "organic_traffic": competitor.organic_traffic,
            "organic_keywords": competitor.organic_keywords,
            "paid_keywords": competitor.paid_keywords,
            "total_backlinks": competitor.total_backlinks,
            "referring_domains": competitor.referring_domains,
            "estimated_ad_spend": competitor.estimated_ad_spend,
            "estimated_ad_keywords": competitor.estimated_ad_keywords,
            "content_score": competitor.content_score,
            "social_followers": competitor.social_followers,
            "technologies": competitor.technologies,
            "social_media": competitor.social_media,
            "notes": competitor.notes,
            "created_at": competitor.created_at,
            "updated_at": competitor.updated_at,
            "last_analyzed_at": competitor.last_analyzed_at,
        }

        if include_snapshots:
            # Load snapshots separately
            snapshots_result = await db.execute(
                select(CompetitorSnapshot)
                .where(CompetitorSnapshot.competitor_id == competitor_id)
                .order_by(desc(CompetitorSnapshot.snapshot_date))
                .limit(30)  # Last 30 snapshots
            )
            snapshots = snapshots_result.scalars().all()

            competitor_dict["snapshots"] = [
                CompetitorSnapshotResponse.model_validate(s) for s in snapshots
            ]
            return CompetitorWithSnapshots(**competitor_dict)
        else:
            return CompetitorResponse(**competitor_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting competitor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get competitor"
        )


@router.patch("/{competitor_id}", response_model=CompetitorResponse)
async def update_competitor(
    competitor_id: str,
    competitor_data: CompetitorUpdate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update competitor information
    """
    try:
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id == competitor_id,
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found"
            )

        # Update fields
        update_data = competitor_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(competitor, field, value)

        competitor.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(competitor)

        logger.info(f"✅ Updated competitor {competitor_id}")
        return CompetitorResponse.model_validate(competitor)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error updating competitor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update competitor"
        )


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competitor(
    competitor_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a competitor (cascade deletes snapshots)
    """
    try:
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id == competitor_id,
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found"
            )

        await db.delete(competitor)
        await db.commit()

        logger.info(f"✅ Deleted competitor {competitor_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error deleting competitor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete competitor"
        )


@router.post("/{competitor_id}/analyze", response_model=CompetitorResponse)
async def analyze_competitor(
    competitor_id: str,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger competitor analysis

    Fetches latest metrics and creates a new snapshot.
    """
    try:
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id == competitor_id,
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found"
            )

        # Trigger background analysis
        background_tasks.add_task(analyze_competitor_domain, competitor_id)

        logger.info(f"✅ Triggered analysis for competitor {competitor.domain}")
        return CompetitorResponse.model_validate(competitor)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error triggering competitor analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger analysis"
        )


@router.get("/{competitor_id}/keywords", response_model=List[dict])
async def get_competitor_keywords(
    competitor_id: str,
    limit: int = 100,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get competitor's ranking keywords
    """
    try:
        logger.info(f"📥 GET /competitors/{competitor_id}/keywords - user_id: {current_user.get('id')}, limit: {limit}")
        # Verify competitor ownership
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id == competitor_id,
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found"
            )

        # Get keywords from DataForSEO
        dataforseo = DataForSEOClient()
        keywords = await dataforseo.get_competitor_keywords(
            competitor.domain,
            limit=limit
        )

        return keywords

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting competitor keywords: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get competitor keywords"
        )


@router.get("/{competitor_id}/gap-analysis", response_model=CompetitorGapAnalysis)
async def get_keyword_gap(
    competitor_id: str,
    user_domain: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze keyword gaps between user and competitor

    Shows keywords the competitor ranks for but you don't.
    """
    try:
        logger.info(f"📥 GET /competitors/{competitor_id}/gap-analysis - user_id: {current_user.get('id')}, user_domain: {user_domain}")
        # Verify competitor ownership
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id == competitor_id,
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found"
            )

        # Get keywords for both domains
        dataforseo = DataForSEOClient()

        competitor_keywords = await dataforseo.get_competitor_keywords(
            competitor.domain,
            limit=500
        )
        user_keywords = await dataforseo.get_competitor_keywords(
            user_domain,
            limit=500
        )

        # Find gaps
        user_kw_set = {k.get("keyword") for k in user_keywords}
        gaps = [
            k for k in competitor_keywords
            if k.get("keyword") not in user_kw_set
        ]

        # Sort by search volume
        high_value_gaps = sorted(
            gaps,
            key=lambda x: x.get("search_volume", 0),
            reverse=True
        )[:50]

        return CompetitorGapAnalysis(
            competitor_domain=competitor.domain,
            total_gap_keywords=len(gaps),
            high_value_gaps=[
                {
                    "keyword": k.get("keyword"),
                    "search_volume": k.get("search_volume"),
                    "difficulty": k.get("keyword_difficulty"),
                    "estimated_traffic": k.get("etv"),
                }
                for k in high_value_gaps
            ],
            content_gaps=[]  # TODO: Implement content gap analysis
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error analyzing keyword gap: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze keyword gap"
        )


# ============================================
# Advanced Analysis Endpoints
# ============================================

@router.get("/{competitor_id}/trends", response_model=CompetitorTrendsResponse)
async def get_competitor_trends(
    competitor_id: str,
    time_range: str = "30d",
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get historical trend data for a competitor

    Time ranges: 7d, 30d, 90d, 1y
    """
    try:
        logger.info(f"📥 GET /competitors/{competitor_id}/trends - range: {time_range}")

        # Verify ownership
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id == competitor_id,
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found"
            )

        service = CompetitorAnalysisService(db)
        try:
            trends = await service.get_trends(UUID(competitor_id), time_range)
            return trends
        finally:
            await service.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get competitor trends"
        )


@router.get("/{competitor_id}/backlinks", response_model=BacklinkProfileResponse)
async def get_backlink_profile(
    competitor_id: str,
    limit: int = 100,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed backlink profile for a competitor
    """
    try:
        logger.info(f"📥 GET /competitors/{competitor_id}/backlinks - limit: {limit}")

        # Verify ownership
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id == competitor_id,
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found"
            )

        service = CompetitorAnalysisService(db)
        try:
            profile = await service.get_backlink_profile(UUID(competitor_id), limit)
            return profile
        finally:
            await service.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting backlink profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get backlink profile"
        )


@router.get("/{competitor_id}/content-gap", response_model=ContentGapResponse)
async def get_content_gaps(
    competitor_id: str,
    user_domain: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Identify content gap opportunities
    """
    try:
        logger.info(f"📥 GET /competitors/{competitor_id}/content-gap")

        # Verify ownership
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id == competitor_id,
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found"
            )

        service = CompetitorAnalysisService(db)
        try:
            gaps = await service.get_content_gaps(UUID(competitor_id), user_domain)
            return gaps
        finally:
            await service.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting content gaps: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get content gaps"
        )


@router.get("/{competitor_id}/ad-intel", response_model=AdIntelligenceResponse)
async def get_ad_intelligence(
    competitor_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get advertising intelligence for a competitor
    """
    try:
        logger.info(f"📥 GET /competitors/{competitor_id}/ad-intel")

        # Verify ownership
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id == competitor_id,
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found"
            )

        service = CompetitorAnalysisService(db)
        try:
            ad_intel = await service.get_ad_intelligence(UUID(competitor_id))
            return ad_intel
        finally:
            await service.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting ad intelligence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ad intelligence"
        )


@router.get("/{competitor_id}/tech-stack", response_model=TechStackResponse)
async def get_tech_stack(
    competitor_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Detect technology stack for a competitor
    """
    try:
        logger.info(f"📥 GET /competitors/{competitor_id}/tech-stack")

        # Verify ownership
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id == competitor_id,
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found"
            )

        service = CompetitorAnalysisService(db)
        try:
            tech = await service.get_tech_stack(UUID(competitor_id))
            return tech
        finally:
            await service.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting tech stack: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tech stack"
        )


@router.post("/{competitor_id}/ai-insights", response_model=CompetitorInsights)
async def generate_ai_insights(
    competitor_id: str,
    request: AIInsightsRequest = AIInsightsRequest(),
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI-powered SWOT analysis and recommendations

    Set regenerate=true to force fresh analysis (ignores cache)
    """
    try:
        logger.info(f"📥 POST /competitors/{competitor_id}/ai-insights - regenerate: {request.regenerate}")

        # Verify ownership
        result = await db.execute(
            select(Competitor).where(
                and_(
                    Competitor.id == competitor_id,
                    Competitor.user_id == current_user.get('id')
                )
            )
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competitor not found"
            )

        service = CompetitorAnalysisService(db)
        try:
            insights = await service.generate_ai_insights(UUID(competitor_id), request.regenerate)

            # Convert generated_at back to datetime if string
            if isinstance(insights.get("generated_at"), str):
                insights["generated_at"] = datetime.fromisoformat(insights["generated_at"])

            return CompetitorInsights(**insights)
        finally:
            await service.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating AI insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI insights"
        )
