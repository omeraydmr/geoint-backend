"""
Keywords API Endpoints

Provides endpoints for:
- Keyword CRUD operations
- Turkish NLP analysis
- Keyword metrics from Google Ads & DataForSEO
- Keyword tracking and monitoring
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from typing import Dict,  List, Optional
import logging
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.keyword import Keyword
from app.schemas.keyword import (
    KeywordCreate,
    KeywordUpdate,
    KeywordResponse,
    KeywordWithScores,
)
from app.schemas.geoint import KeywordAnalysisRequest, KeywordAnalysisResponse
from app.services.nlp.turkish_analyzer import TurkishNLPAnalyzer
from app.services.external.google_ads import GoogleAdsClient
from app.services.external.dataforseo import DataForSEOClient

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# Helper Functions
# ============================================

async def analyze_and_enrich_keyword(keyword_id: str, db: AsyncSession):
    """
    Background task to analyze keyword and fetch metrics
    """
    try:
        result = await db.execute(
            select(Keyword).where(Keyword.id == keyword_id)
        )
        keyword = result.scalar_one_or_none()

        if not keyword:
            logger.error(f"Keyword {keyword_id} not found")
            return

        # NLP Analysis
        nlp = TurkishNLPAnalyzer()
        analysis = nlp.analyze_keyword(keyword.keyword)

        keyword.root_form = analysis["root_form"]
        keyword.intent = analysis["intent"]
        keyword.nlp_metadata = {
            "pos": analysis.get("pos"),
            "variations": analysis.get("variations", []),
            "is_valid": analysis["is_valid"]
        }

        # Get metrics from DataForSEO (primary source - more reliable)
        dataforseo = DataForSEOClient()
        seo_metrics = await dataforseo.get_keyword_metrics([keyword.keyword])

        if seo_metrics:
            first_metric = seo_metrics[0]
            keyword.avg_monthly_searches = first_metric.get("search_volume", 0)
            keyword.cpc_avg = int(first_metric.get("cpc", 0) * 100)  # Store as cents

        # Fallback to Google Ads if DataForSEO didn't return data
        if not keyword.avg_monthly_searches:
            google_ads = GoogleAdsClient()
            keyword_ideas = await google_ads.get_keyword_ideas([keyword.keyword])

            if keyword_ideas:
                first_result = keyword_ideas[0]
                keyword.avg_monthly_searches = first_result.get("search_volume", 0)
                keyword.cpc_avg = int(first_result.get("cpc_avg", 0) * 100)  # Store as cents

        keyword.last_refreshed_at = datetime.utcnow()
        await db.commit()

        logger.info(f"✅ Analyzed and enriched keyword {keyword.keyword}")

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error analyzing keyword {keyword_id}: {e}")


# ============================================
# Keyword Endpoints
# ============================================

@router.get("/", response_model=List[KeywordResponse])
async def list_keywords(
    skip: int = 0,
    limit: int = 50,
    is_active: Optional[bool] = None,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all keywords for the current user

    Filters:
    - is_active: filter by active status
    """
    try:
        logger.info(f"📥 GET /keywords - user_id: {current_user.get('id')}, skip: {skip}, limit: {limit}, is_active: {is_active}")
        query = select(Keyword).where(Keyword.user_id == current_user.get('id'))

        if is_active is not None:
            query = query.where(Keyword.is_active == is_active)

        query = query.order_by(Keyword.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        keywords = result.scalars().all()

        logger.info(f"📤 GET /keywords - returning {len(keywords)} keywords")
        return [KeywordResponse.model_validate(k) for k in keywords]

    except Exception as e:
        logger.error(f"❌ Error listing keywords: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list keywords"
        )


@router.post("/", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
async def create_keyword(
    keyword_data: KeywordCreate,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new keyword and trigger analysis

    Automatically triggers:
    - Turkish NLP analysis
    - Google Ads metrics fetch
    - DataForSEO metrics fetch
    """
    try:
        # Check if keyword already exists
        existing = await db.execute(
            select(Keyword).where(
                and_(
                    Keyword.user_id == current_user.get('id'),
                    Keyword.keyword == keyword_data.keyword
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Keyword already exists"
            )

        # Create keyword
        keyword = Keyword(
            user_id=current_user.get('id'),
            **keyword_data.model_dump()
        )

        db.add(keyword)
        await db.commit()
        await db.refresh(keyword)

        # Trigger background analysis
        background_tasks.add_task(analyze_and_enrich_keyword, str(keyword.id), db)

        logger.info(f"✅ Created keyword {keyword.keyword} for user {current_user.get('id')}")
        return KeywordResponse.model_validate(keyword)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error creating keyword: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create keyword"
        )


@router.get("/{keyword_id}", response_model=KeywordResponse)
async def get_keyword(
    keyword_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single keyword
    """
    try:
        result = await db.execute(
            select(Keyword).where(
                and_(
                    Keyword.id == keyword_id,
                    Keyword.user_id == current_user.get('id')
                )
            )
        )
        keyword = result.scalar_one_or_none()

        if not keyword:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword not found"
            )

        return KeywordResponse.model_validate(keyword)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting keyword: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get keyword"
        )


@router.patch("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: str,
    keyword_data: KeywordUpdate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a keyword
    """
    try:
        result = await db.execute(
            select(Keyword).where(
                and_(
                    Keyword.id == keyword_id,
                    Keyword.user_id == current_user.get('id')
                )
            )
        )
        keyword = result.scalar_one_or_none()

        if not keyword:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword not found"
            )

        # Update fields
        update_data = keyword_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(keyword, field, value)

        keyword.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(keyword)

        logger.info(f"✅ Updated keyword {keyword_id}")
        return KeywordResponse.model_validate(keyword)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error updating keyword: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update keyword"
        )


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    keyword_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a keyword (cascade deletes GEOINT scores)
    """
    try:
        result = await db.execute(
            select(Keyword).where(
                and_(
                    Keyword.id == keyword_id,
                    Keyword.user_id == current_user.get('id')
                )
            )
        )
        keyword = result.scalar_one_or_none()

        if not keyword:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword not found"
            )

        await db.delete(keyword)
        await db.commit()

        logger.info(f"✅ Deleted keyword {keyword_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error deleting keyword: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete keyword"
        )


@router.post("/{keyword_id}/refresh", response_model=KeywordResponse)
async def refresh_keyword(
    keyword_id: str,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually refresh keyword metrics

    Triggers background analysis to update:
    - Search volume
    - CPC data
    - Trends
    """
    try:
        result = await db.execute(
            select(Keyword).where(
                and_(
                    Keyword.id == keyword_id,
                    Keyword.user_id == current_user.get('id')
                )
            )
        )
        keyword = result.scalar_one_or_none()

        if not keyword:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword not found"
            )

        # Trigger background analysis
        background_tasks.add_task(analyze_and_enrich_keyword, keyword_id, db)

        logger.info(f"✅ Triggered refresh for keyword {keyword.keyword}")
        return KeywordResponse.model_validate(keyword)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error refreshing keyword: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh keyword"
        )


# ============================================
# NLP Analysis Endpoint
# ============================================

@router.post("/analyze", response_model=KeywordAnalysisResponse)
async def analyze_keyword_text(
    request: KeywordAnalysisRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Analyze a keyword using Turkish NLP

    Does NOT save to database - just returns analysis.
    Useful for preview before creating a keyword.
    """
    try:
        nlp = TurkishNLPAnalyzer()
        analysis = nlp.analyze_keyword(request.keyword)

        return KeywordAnalysisResponse(**analysis)

    except Exception as e:
        logger.error(f"❌ Error analyzing keyword: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze keyword"
        )


# ============================================
# Keyword Metrics Endpoint
# ============================================

@router.get("/{keyword_id}/metrics", response_model=dict)
async def get_keyword_metrics(
    keyword_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed metrics for a keyword from multiple sources

    Returns data from:
    - Google Ads API (keyword ideas, competition, CPC)
    - DataForSEO (search volume, difficulty, SERP features)
    - Database (stored historical data)
    """
    try:
        # Get keyword from database
        result = await db.execute(
            select(Keyword).where(
                and_(
                    Keyword.id == keyword_id,
                    Keyword.user_id == current_user.get('id')
                )
            )
        )
        keyword = result.scalar_one_or_none()

        if not keyword:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword not found"
            )

        # Get fresh data from Google Ads
        google_ads = GoogleAdsClient()
        google_metrics = await google_ads.get_keyword_ideas([keyword.keyword])

        # Get fresh data from DataForSEO
        dataforseo = DataForSEOClient()
        seo_metrics = await dataforseo.get_keyword_metrics([keyword.keyword])

        return {
            "keyword": keyword.keyword,
            "database": {
                "avg_monthly_searches": keyword.avg_monthly_searches,
                "cpc_avg": keyword.cpc_avg / 100 if keyword.cpc_avg else None,
                "root_form": keyword.root_form,
                "intent": keyword.intent,
                "last_refreshed": keyword.last_refreshed_at,
            },
            "google_ads": google_metrics[0] if google_metrics else None,
            "dataforseo": seo_metrics[0] if seo_metrics else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting keyword metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get keyword metrics"
        )


# ============================================
# Batch Operations
# ============================================

@router.post("/batch", response_model=List[KeywordResponse], status_code=status.HTTP_201_CREATED)
async def create_keywords_batch(
    keywords: List[KeywordCreate],
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create multiple keywords at once

    Useful for importing keyword lists.
    Each keyword will be analyzed in background.
    """
    try:
        created_keywords = []

        for keyword_data in keywords:
            # Check if keyword already exists
            existing = await db.execute(
                select(Keyword).where(
                    and_(
                        Keyword.user_id == current_user.get('id'),
                        Keyword.keyword == keyword_data.keyword
                    )
                )
            )
            if existing.scalar_one_or_none():
                logger.warning(f"⚠️ Skipping duplicate keyword: {keyword_data.keyword}")
                continue

            # Create keyword
            keyword = Keyword(
                user_id=current_user.get('id'),
                **keyword_data.model_dump()
            )

            db.add(keyword)
            created_keywords.append(keyword)

        await db.commit()

        # Refresh all
        for keyword in created_keywords:
            await db.refresh(keyword)
            # Trigger background analysis
            background_tasks.add_task(analyze_and_enrich_keyword, str(keyword.id), db)

        logger.info(f"✅ Created {len(created_keywords)} keywords in batch")
        return [KeywordResponse.model_validate(k) for k in created_keywords]

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error creating keywords batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create keywords batch"
        )
