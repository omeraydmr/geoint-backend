"""
Media Monitoring & PR API Endpoints

Provides endpoints for:
- Media mention tracking
- Brand sentiment analysis
- PR opportunity identification
- Media analytics and reporting
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func, desc
from typing import Dict,  List, Optional
import logging
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.media import MediaMention, PROpportunity
from app.schemas.media import (
    MediaMentionCreate,
    MediaMentionUpdate,
    MediaMentionResponse,
    MediaMentionSearchRequest,
    PROpportunityCreate,
    PROpportunityUpdate,
    PROpportunityResponse,
    MediaAnalytics,
    PRPerformance,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# Media Mention Endpoints
# ============================================

@router.get("/mentions", response_model=List[MediaMentionResponse])
async def list_media_mentions(
    skip: int = 0,
    limit: int = 50,
    sentiment: Optional[str] = None,
    publication: Optional[str] = None,
    days_back: int = 30,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List media mentions for the current user

    Filters:
    - sentiment: positive, negative, neutral
    - publication: specific publication name
    - days_back: how many days to look back (default 30)
    """
    try:
        logger.info(f"📥 GET /media/mentions - user_id: {current_user.get('id')}, sentiment: {sentiment}, publication: {publication}, days_back: {days_back}")
        query = select(MediaMention).where(MediaMention.user_id == current_user.get('id'))

        # Date filter
        date_threshold = datetime.utcnow() - timedelta(days=days_back)
        query = query.where(MediaMention.discovered_at >= date_threshold)

        # Sentiment filter
        if sentiment:
            query = query.where(MediaMention.sentiment == sentiment)

        # Publication filter
        if publication:
            query = query.where(MediaMention.publication == publication)

        query = query.order_by(desc(MediaMention.published_at)).offset(skip).limit(limit)

        result = await db.execute(query)
        mentions = result.scalars().all()

        logger.info(f"📤 GET /media/mentions - returning {len(mentions)} mentions")
        return [MediaMentionResponse.model_validate(m) for m in mentions]

    except Exception as e:
        logger.error(f"❌ Error listing media mentions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list media mentions"
        )


@router.post("/mentions", response_model=MediaMentionResponse, status_code=status.HTTP_201_CREATED)
async def create_media_mention(
    mention_data: MediaMentionCreate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a media mention manually
    """
    try:
        # Check if URL already exists
        existing = await db.execute(
            select(MediaMention).where(
                and_(
                    MediaMention.user_id == current_user.get('id'),
                    MediaMention.url == mention_data.url
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Media mention with this URL already exists"
            )

        mention = MediaMention(
            user_id=current_user.get('id'),
            **mention_data.model_dump()
        )

        db.add(mention)
        await db.commit()
        await db.refresh(mention)

        logger.info(f"✅ Created media mention {mention.id}")
        return MediaMentionResponse.model_validate(mention)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error creating media mention: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create media mention"
        )


@router.get("/mentions/{mention_id}", response_model=MediaMentionResponse)
async def get_media_mention(
    mention_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single media mention
    """
    try:
        logger.info(f"📥 GET /media/mentions/{mention_id} - user_id: {current_user.get('id')}")
        result = await db.execute(
            select(MediaMention).where(
                and_(
                    MediaMention.id == mention_id,
                    MediaMention.user_id == current_user.get('id')
                )
            )
        )
        mention = result.scalar_one_or_none()

        if not mention:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media mention not found"
            )

        return MediaMentionResponse.model_validate(mention)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting media mention: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get media mention"
        )


@router.patch("/mentions/{mention_id}", response_model=MediaMentionResponse)
async def update_media_mention(
    mention_id: str,
    mention_data: MediaMentionUpdate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a media mention (e.g., add sentiment analysis)
    """
    try:
        result = await db.execute(
            select(MediaMention).where(
                and_(
                    MediaMention.id == mention_id,
                    MediaMention.user_id == current_user.get('id')
                )
            )
        )
        mention = result.scalar_one_or_none()

        if not mention:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media mention not found"
            )

        # Update fields
        update_data = mention_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(mention, field, value)

        await db.commit()
        await db.refresh(mention)

        logger.info(f"✅ Updated media mention {mention_id}")
        return MediaMentionResponse.model_validate(mention)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error updating media mention: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update media mention"
        )


@router.delete("/mentions/{mention_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media_mention(
    mention_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a media mention
    """
    try:
        result = await db.execute(
            select(MediaMention).where(
                and_(
                    MediaMention.id == mention_id,
                    MediaMention.user_id == current_user.get('id')
                )
            )
        )
        mention = result.scalar_one_or_none()

        if not mention:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media mention not found"
            )

        await db.delete(mention)
        await db.commit()

        logger.info(f"✅ Deleted media mention {mention_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error deleting media mention: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete media mention"
        )


@router.get("/mentions/analytics", response_model=MediaAnalytics)
async def get_media_analytics(
    days_back: int = 30,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get media mention analytics for the past N days
    """
    try:
        logger.info(f"📥 GET /media/mentions/analytics - user_id: {current_user.get('id')}, days_back: {days_back}")
        date_threshold = datetime.utcnow() - timedelta(days=days_back)

        # Get all mentions in period
        result = await db.execute(
            select(MediaMention).where(
                and_(
                    MediaMention.user_id == current_user.get('id'),
                    MediaMention.discovered_at >= date_threshold
                )
            )
        )
        mentions = result.scalars().all()

        # Calculate metrics
        total_mentions = len(mentions)
        positive_mentions = len([m for m in mentions if m.sentiment == "positive"])
        negative_mentions = len([m for m in mentions if m.sentiment == "negative"])
        neutral_mentions = len([m for m in mentions if m.sentiment == "neutral"])
        total_reach = sum(m.estimated_reach or 0 for m in mentions)
        total_shares = sum(m.social_shares or 0 for m in mentions)

        sentiment_scores = [m.sentiment_score for m in mentions if m.sentiment_score is not None]
        avg_sentiment_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0

        # Top publications
        publication_counts = {}
        for m in mentions:
            if m.publication:
                publication_counts[m.publication] = publication_counts.get(m.publication, 0) + 1

        top_publications = [
            {"publication": pub, "count": count}
            for pub, count in sorted(publication_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # Mentions by day
        mentions_by_day = {}
        for m in mentions:
            day = m.discovered_at.date().isoformat()
            mentions_by_day[day] = mentions_by_day.get(day, 0) + 1

        mentions_by_day_list = [
            {"date": day, "count": count}
            for day, count in sorted(mentions_by_day.items())
        ]

        return MediaAnalytics(
            total_mentions=total_mentions,
            positive_mentions=positive_mentions,
            negative_mentions=negative_mentions,
            neutral_mentions=neutral_mentions,
            total_reach=total_reach,
            total_shares=total_shares,
            avg_sentiment_score=avg_sentiment_score,
            top_publications=top_publications,
            mentions_by_day=mentions_by_day_list
        )

    except Exception as e:
        logger.error(f"❌ Error getting media analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get media analytics"
        )


# ============================================
# PR Opportunity Endpoints
# ============================================

@router.get("/pr-opportunities", response_model=List[PROpportunityResponse])
async def list_pr_opportunities(
    skip: int = 0,
    limit: int = 50,
    contacted: Optional[bool] = None,
    category: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List PR opportunities for the current user

    Filters:
    - contacted: filter by contacted status
    - category: filter by category (tech, marketing, etc.)
    """
    try:
        logger.info(f"📥 GET /media/pr-opportunities - user_id: {current_user.get('id')}, contacted: {contacted}, category: {category}")
        query = select(PROpportunity).where(PROpportunity.user_id == current_user.get('id'))

        if contacted is not None:
            query = query.where(PROpportunity.contacted == contacted)

        if category:
            query = query.where(PROpportunity.category == category)

        query = query.order_by(desc(PROpportunity.relevance_score)).offset(skip).limit(limit)

        result = await db.execute(query)
        opportunities = result.scalars().all()

        logger.info(f"📤 GET /media/pr-opportunities - returning {len(opportunities)} opportunities")
        return [PROpportunityResponse.model_validate(o) for o in opportunities]

    except Exception as e:
        logger.error(f"❌ Error listing PR opportunities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list PR opportunities"
        )


@router.post("/pr-opportunities", response_model=PROpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_pr_opportunity(
    opportunity_data: PROpportunityCreate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a PR opportunity manually
    """
    try:
        opportunity = PROpportunity(
            user_id=current_user.get('id'),
            **opportunity_data.model_dump()
        )

        db.add(opportunity)
        await db.commit()
        await db.refresh(opportunity)

        logger.info(f"✅ Created PR opportunity {opportunity.id}")
        return PROpportunityResponse.model_validate(opportunity)

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error creating PR opportunity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create PR opportunity"
        )


@router.patch("/pr-opportunities/{opportunity_id}", response_model=PROpportunityResponse)
async def update_pr_opportunity(
    opportunity_id: str,
    opportunity_data: PROpportunityUpdate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a PR opportunity (e.g., mark as contacted)
    """
    try:
        result = await db.execute(
            select(PROpportunity).where(
                and_(
                    PROpportunity.id == opportunity_id,
                    PROpportunity.user_id == current_user.get('id')
                )
            )
        )
        opportunity = result.scalar_one_or_none()

        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PR opportunity not found"
            )

        # Update fields
        update_data = opportunity_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(opportunity, field, value)

        # Auto-set contacted_at if contacted is True
        if opportunity_data.contacted and not opportunity.contacted_at:
            opportunity.contacted_at = datetime.utcnow()

        await db.commit()
        await db.refresh(opportunity)

        logger.info(f"✅ Updated PR opportunity {opportunity_id}")
        return PROpportunityResponse.model_validate(opportunity)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error updating PR opportunity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update PR opportunity"
        )


@router.delete("/pr-opportunities/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pr_opportunity(
    opportunity_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a PR opportunity
    """
    try:
        result = await db.execute(
            select(PROpportunity).where(
                and_(
                    PROpportunity.id == opportunity_id,
                    PROpportunity.user_id == current_user.get('id')
                )
            )
        )
        opportunity = result.scalar_one_or_none()

        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PR opportunity not found"
            )

        await db.delete(opportunity)
        await db.commit()

        logger.info(f"✅ Deleted PR opportunity {opportunity_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error deleting PR opportunity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete PR opportunity"
        )
