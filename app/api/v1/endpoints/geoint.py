"""
GEOINT API Endpoints

Provides geographic intelligence data and analysis
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import logging

from app.core.database import get_db
from app.core.cache import cache, cache_invalidate
from app.core.config import settings
from app.core.security import get_current_user
from app.models.geo import Province, District, GEOINTScore, RegionType
from app.models.keyword import Keyword
from app.schemas.geoint import (
    HeatmapResponse,
    TopRegionResponse,
    BudgetRecommendationRequest,
    BudgetAllocation,
    GEOINTScoreResponse,
    RegionTypeEnum,
    CompetitorComparisonResponse,
    RegionCompetitorData,
    CompetitorComparisonSummary,
    ComparisonHistoryItem,
    ComparisonHistoryListResponse,
)
from app.services.geoint import GEOINTCalculator, HeatmapGenerator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/heatmap/{keyword_id}", response_model=HeatmapResponse)
@cache(ttl=settings.CACHE_GEOINT_TTL, key_prefix="geoint:heatmap")
async def get_heatmap(
    keyword_id: str,
    region_type: str = Query("il", description="Region type: il, ilce, mahalle"),
    province_id: Optional[str] = Query(None, description="Province ID for district filtering"),
    include_geometry: bool = Query(True, description="Include full geometry"),
    force: bool = Query(False, description="Force refresh from database"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get GeoJSON heatmap for a keyword

    Returns choropleth map data with GEOINT scores for visualization.
    Cached for 15 minutes for optimal performance.
    """
    logger.info(f"GET /geoint/heatmap/{keyword_id} - region_type: {region_type}, province_id: {province_id}, force: {force}")
    
    if force:
        # Explicitly invalidate cache for this specific request
        await cache_invalidate(f"geoint:heatmap:{keyword_id}*")

    # Verify keyword exists
    keyword = await db.get(Keyword, keyword_id)
    if not keyword:
        logger.warning(f"⚠️ Keyword not found: {keyword_id}")
        raise HTTPException(status_code=404, detail="Keyword not found")

    # Generate heatmap
    heatmap_gen = HeatmapGenerator(db)

    if region_type == "il":
        heatmap = await heatmap_gen.generate_province_heatmap(
            keyword_id,
            include_geometry=include_geometry
        )
    elif region_type == "ilce":
        heatmap = await heatmap_gen.generate_district_heatmap(
            keyword_id,
            province_id=province_id,
            include_geometry=include_geometry
        )
    else:
        logger.warning(f"⚠️ Invalid region_type: {region_type}")
        raise HTTPException(status_code=400, detail="Invalid region_type")

    logger.info(f"📤 GET /geoint/heatmap/{keyword_id} - returning heatmap data")
    return heatmap


@router.get("/top-regions/{keyword_id}", response_model=List[TopRegionResponse])
@cache(ttl=settings.CACHE_GEOINT_TTL, key_prefix="geoint:top_regions")
async def get_top_regions(
    keyword_id: str,
    limit: int = Query(10, ge=1, le=100),
    region_type: Optional[str] = Query(None, description="Filter by region type"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top regions by GEOINT score for a keyword

    Returns ranked list of regions with highest opportunity scores.
    Cached for 15 minutes for optimal performance.
    """
    try:
        logger.info(f"GET /geoint/top-regions/{keyword_id} - limit: {limit}, region_type: {region_type}")
        # Verify keyword exists
        keyword = await db.get(Keyword, keyword_id)
        if not keyword:
            logger.warning(f"⚠️ Keyword not found: {keyword_id}")
            raise HTTPException(status_code=404, detail="Keyword not found")

        # Map region type
        region_type_enum = None
        if region_type:
            region_type_map = {
                "il": RegionType.PROVINCE,
                "ilce": RegionType.DISTRICT,
                "mahalle": RegionType.NEIGHBORHOOD
            }
            region_type_enum = region_type_map.get(region_type)

        # Get top regions
        calculator = GEOINTCalculator(db)
        top_regions = await calculator.get_top_regions(
            keyword_id,
            region_type=region_type_enum,
            limit=limit
        )

        logger.info(f"📊 Retrieved {len(top_regions)} scores from database")

        # Convert to response format
        heatmap_gen = HeatmapGenerator(db)
        results = []

        for idx, score in enumerate(top_regions):
            try:
                region_name = await heatmap_gen._get_region_name(score.region_id, score.region_type, score.raw_data)

                results.append(TopRegionResponse(
                    region_id=str(score.region_id),
                    region_name=region_name,
                    region_type=score.region_type.value,
                    geoint_score=score.geoint_score,
                    search_index=score.search_index,
                    trend_score=score.trend_score,
                    demographic_fit=score.demographic_fit,
                    competition_gap=score.competition_gap,
                    trend_direction=score.trend_direction or "stable",
                    calculated_at=score.calculated_at
                ))
            except Exception as e:
                logger.error(f"❌ Error processing score #{idx+1} (region_id={score.region_id}): {type(e).__name__}: {e}")
                raise

        logger.info(f"📤 GET /geoint/top-regions/{keyword_id} - returning {len(results)} regions")
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in get_top_regions: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving top regions: {str(e)}")


@router.post("/budget-recommendation", response_model=List[BudgetAllocation])
async def get_budget_recommendation(
    request: BudgetRecommendationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-powered budget allocation recommendations

    Distributes budget across top regions based on GEOINT scores
    and provides channel recommendations.
    """
    logger.info(f"📥 POST /geoint/budget-recommendation - keyword_id: {request.keyword_id}, total_budget: {request.total_budget}, top_n: {request.top_n}")
    # Verify keyword exists
    keyword = await db.get(Keyword, request.keyword_id)
    if not keyword:
        logger.warning(f"⚠️ Keyword not found: {request.keyword_id}")
        raise HTTPException(status_code=404, detail="Keyword not found")

    # Map region type
    region_type_map = {
        RegionTypeEnum.PROVINCE: RegionType.PROVINCE,
        RegionTypeEnum.DISTRICT: RegionType.DISTRICT,
        RegionTypeEnum.NEIGHBORHOOD: RegionType.NEIGHBORHOOD
    }
    region_type = region_type_map[request.region_type]

    # Get recommendations
    heatmap_gen = HeatmapGenerator(db)
    recommendations = await heatmap_gen.generate_budget_recommendation(
        request.keyword_id,
        request.total_budget,
        region_type=region_type,
        top_n=request.top_n
    )

    logger.info(f"📤 POST /geoint/budget-recommendation - returning {len(recommendations)} allocations")
    return [BudgetAllocation(**rec) for rec in recommendations]


@router.get("/score/{keyword_id}/{region_id}", response_model=GEOINTScoreResponse)
async def get_score_details(
    keyword_id: str,
    region_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed GEOINT score breakdown for a specific region

    Returns all components and metadata for a keyword-region pair.
    """
    logger.info(f"📥 GET /geoint/score/{keyword_id}/{region_id}")
    # Query score
    result = await db.execute(
        select(GEOINTScore).where(
            GEOINTScore.keyword_id == keyword_id,
            GEOINTScore.region_id == region_id
        )
    )
    score = result.scalar_one_or_none()

    if not score:
        logger.warning(f"⚠️ Score not found for keyword: {keyword_id}, region: {region_id}")
        raise HTTPException(status_code=404, detail="Score not found")

    # Get region name
    heatmap_gen = HeatmapGenerator(db)
    region_name = await heatmap_gen._get_region_name(score.region_id, score.region_type, score.raw_data)

    logger.info(f"📤 GET /geoint/score/{keyword_id}/{region_id} - score: {score.geoint_score}")
    return GEOINTScoreResponse(
        id=str(score.id),
        keyword_id=str(score.keyword_id),
        region_type=score.region_type.value,
        region_id=str(score.region_id),
        region_name=region_name,
        search_index=score.search_index,
        trend_score=score.trend_score,
        demographic_fit=score.demographic_fit,
        competition_gap=score.competition_gap,
        geoint_score=score.geoint_score,
        trend_direction=score.trend_direction,
        trend_change_pct=score.trend_change_pct,
        calculated_at=score.calculated_at
    )


@router.post("/calculate/{keyword_id}")
async def trigger_score_calculation(
    keyword_id: str,
    force: bool = Query(False, description="Force recalculation"),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger GEOINT score calculation for a keyword

    Calculates scores for all regions. This is typically done
    automatically but can be manually triggered.
    """
    logger.info(f"📥 POST /geoint/calculate/{keyword_id} - force: {force}")
    # Verify keyword exists
    keyword = await db.get(Keyword, keyword_id)
    if not keyword:
        logger.warning(f"⚠️ Keyword not found: {keyword_id}")
        raise HTTPException(status_code=404, detail="Keyword not found")

    # Execute GEOINT score calculation directly
    try:
        # Execute processor directly (APScheduler handles scheduled tasks)
        from app.services.geoint.processor import GEOINTProcessor
        processor = GEOINTProcessor(db)
        result = await processor.process_keyword(keyword_id)
        
        # CLEAR CACHE after new scores are saved
        await cache_invalidate(f"geoint:heatmap:{keyword_id}*")
        await cache_invalidate(f"geoint:top_regions:{keyword_id}*")
        
        logger.info(f"✅ POST /geoint/calculate/{keyword_id} - Sync calculation and cache invalidation completed")
        return {
            "message": "Score calculation completed successfully",
            "task_id": "sync-execution",
            "keyword_id": keyword_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"GEOINT processor failed for keyword {keyword_id}: {e}", exc_info=True)

        # Rollback the failed transaction to avoid leaving the session dirty
        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Score calculation failed: {str(e)}"
        )


@router.get("/stats/{keyword_id}")
async def get_geoint_stats(
    keyword_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get GEOINT statistics summary for a keyword

    Returns aggregate stats for dashboard display.
    """
    logger.info(f"📥 GET /geoint/stats/{keyword_id}")
    # Verify keyword exists
    keyword = await db.get(Keyword, keyword_id)
    if not keyword:
        logger.warning(f"⚠️ Keyword not found: {keyword_id}")
        raise HTTPException(status_code=404, detail="Keyword not found")

    # Get aggregate stats
    result = await db.execute(
        select(
            func.count(GEOINTScore.id).label("total_regions"),
            func.avg(GEOINTScore.geoint_score).label("avg_score"),
            func.max(GEOINTScore.geoint_score).label("max_score"),
            func.min(GEOINTScore.geoint_score).label("min_score"),
        ).where(GEOINTScore.keyword_id == keyword_id)
    )
    stats = result.first()

    # Count high potential regions (score >= 70)
    high_potential_result = await db.execute(
        select(func.count(GEOINTScore.id)).where(
            GEOINTScore.keyword_id == keyword_id,
            GEOINTScore.geoint_score >= 70
        )
    )
    high_potential = high_potential_result.scalar() or 0

    # Count medium potential (40-70)
    medium_potential_result = await db.execute(
        select(func.count(GEOINTScore.id)).where(
            GEOINTScore.keyword_id == keyword_id,
            GEOINTScore.geoint_score >= 40,
            GEOINTScore.geoint_score < 70
        )
    )
    medium_potential = medium_potential_result.scalar() or 0

    # Count low potential (<40)
    low_potential_result = await db.execute(
        select(func.count(GEOINTScore.id)).where(
            GEOINTScore.keyword_id == keyword_id,
            GEOINTScore.geoint_score < 40
        )
    )
    low_potential = low_potential_result.scalar() or 0

    # Get trend distribution
    trend_up_result = await db.execute(
        select(func.count(GEOINTScore.id)).where(
            GEOINTScore.keyword_id == keyword_id,
            GEOINTScore.trend_direction == "up"
        )
    )
    trend_up = trend_up_result.scalar() or 0

    trend_down_result = await db.execute(
        select(func.count(GEOINTScore.id)).where(
            GEOINTScore.keyword_id == keyword_id,
            GEOINTScore.trend_direction == "down"
        )
    )
    trend_down = trend_down_result.scalar() or 0

    logger.info(f"📤 GET /geoint/stats/{keyword_id} - total_regions: {stats.total_regions or 0}, avg_score: {round(stats.avg_score or 0, 1)}")
    return {
        "keyword_id": keyword_id,
        "keyword": keyword.keyword,
        "total_regions": stats.total_regions or 0,
        "avg_score": round(stats.avg_score or 0, 1),
        "max_score": round(stats.max_score or 0, 1),
        "min_score": round(stats.min_score or 0, 1),
        "high_potential_count": high_potential,
        "medium_potential_count": medium_potential,
        "low_potential_count": low_potential,
        "distribution": {
            "high": high_potential,
            "medium": medium_potential,
            "low": low_potential
        },
        "trends": {
            "up": trend_up,
            "down": trend_down,
            "stable": (stats.total_regions or 0) - trend_up - trend_down
        }
    }


@router.get("/overview")
async def get_geoint_overview(
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall GEOINT system overview

    Returns system-wide statistics.
    """
    logger.info(f"📥 GET /geoint/overview")
    # Count provinces
    province_count = await db.execute(select(func.count(Province.id)))
    total_provinces = province_count.scalar() or 81

    # Count districts
    district_count = await db.execute(select(func.count(District.id)))
    total_districts = district_count.scalar() or 973

    # Total keywords with GEOINT data
    keyword_count = await db.execute(
        select(func.count(func.distinct(GEOINTScore.keyword_id)))
    )
    keywords_with_data = keyword_count.scalar() or 0

    # Total GEOINT scores
    score_count = await db.execute(select(func.count(GEOINTScore.id)))
    total_scores = score_count.scalar() or 0

    logger.info(f"📤 GET /geoint/overview - provinces: {total_provinces}, districts: {total_districts}, scores: {total_scores}")
    return {
        "total_provinces": total_provinces,
        "total_districts": total_districts,
        "total_neighborhoods": 32000,  # Approximate
        "keywords_with_geoint": keywords_with_data,
        "total_geoint_scores": total_scores
    }


# ============================================
# Competitor Comparison Endpoints
# ============================================

@router.get("/competitor-comparison/{keyword_id}", response_model=CompetitorComparisonResponse)
async def get_competitor_comparison(
    keyword_id: str,
    competitor_domains: List[str] = Query(..., description="Competitor domains to compare"),
    user_domain: Optional[str] = Query(None, description="Your domain for comparison"),
    region_type: str = Query("il", description="Region type: il (province) or ilce (district)"),
    province_id: Optional[str] = Query(None, description="Province ID for district filtering"),
    force: bool = Query(False, description="Force refresh, bypass cache"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get SERP position comparison for a keyword across regions.

    Compares your domain's SERP positions against competitors
    across Turkish provinces or districts.

    - **keyword_id**: The keyword to analyze
    - **competitor_domains**: List of competitor domains (max 4)
    - **user_domain**: Your domain (optional)
    - **region_type**: "il" for provinces, "ilce" for districts
    - **province_id**: Required when region_type is "ilce"
    """
    logger.info(f"GET /geoint/competitor-comparison/{keyword_id} - competitors: {competitor_domains}, user_domain: {user_domain}")

    # Validate keyword exists
    keyword = await db.get(Keyword, keyword_id)
    if not keyword:
        logger.warning(f"⚠️ Keyword not found: {keyword_id}")
        raise HTTPException(status_code=404, detail="Keyword not found")

    # Limit competitors
    if len(competitor_domains) > 4:
        raise HTTPException(status_code=400, detail="Maximum 4 competitors allowed")

    if len(competitor_domains) < 1:
        raise HTTPException(status_code=400, detail="At least 1 competitor required")

    # Build domains list
    all_domains = list(competitor_domains)
    if user_domain and user_domain not in all_domains:
        all_domains.insert(0, user_domain)

    # Get regional SERP positions
    from app.services.external import DataForSEOClient
    from app.services.external.dataforseo import TURKEY_PROVINCE_LOCATION_CODES, TURKEY_PROVINCE_NAMES

    async with DataForSEOClient() as client:
        # Determine which provinces to query
        if region_type == "ilce" and province_id:
            # For district view, just query the single province
            province_codes = [province_id]
        elif settings.COMPETITOR_TEST_MODE:
            # Test mode: only Istanbul (34), Ankara (06), Izmir (35)
            province_codes = ["34", "06", "35"]
            logger.info(
                f"COMPETITOR_TEST_MODE active: querying only {province_codes} "
                "instead of all 81 provinces"
            )
        else:
            # Query all provinces
            province_codes = list(TURKEY_PROVINCE_LOCATION_CODES.keys())

        # Get SERP positions
        regional_data = await client.get_regional_serp_positions(
            keyword=keyword.keyword,
            domains=all_domains,
            province_codes=province_codes
        )

    # Debug log
    sample_data = dict(list(regional_data.items())[:3])
    logger.info(f"📊 Regional data sample (first 3 provinces): {sample_data}")
    logger.info(f"📊 User domain: {user_domain}, All domains: {all_domains}")

    # Build response
    regions: List[RegionCompetitorData] = []
    summary_stats = {
        "total_regions": 0,
        "regions_with_your_data": 0,
        "winning_regions": 0,
        "losing_regions": 0,
        "tied_regions": 0,
        "not_ranking_regions": 0,
        "your_positions": [],
        "competitor_positions": []
    }

    for province_code, positions in regional_data.items():
        province_name = TURKEY_PROVINCE_NAMES.get(province_code, f"Province {province_code}")

        # Calculate your position and best competitor
        your_pos = positions.get(user_domain) if user_domain else None
        competitor_positions = [
            positions.get(d) for d in competitor_domains
            if positions.get(d) is not None
        ]
        best_competitor = min(competitor_positions) if competitor_positions else None

        # Calculate position gap
        position_gap = None
        if your_pos is not None and best_competitor is not None:
            position_gap = your_pos - best_competitor  # Negative = you're behind

        # Update summary stats
        summary_stats["total_regions"] += 1

        if your_pos is not None:
            summary_stats["regions_with_your_data"] += 1
            summary_stats["your_positions"].append(your_pos)

            if best_competitor is not None:
                summary_stats["competitor_positions"].append(best_competitor)
                if your_pos < best_competitor:
                    summary_stats["winning_regions"] += 1
                elif your_pos > best_competitor:
                    summary_stats["losing_regions"] += 1
                else:
                    summary_stats["tied_regions"] += 1
        else:
            if user_domain:
                summary_stats["not_ranking_regions"] += 1

        regions.append(RegionCompetitorData(
            region_id=province_code,
            region_name=province_name,
            positions=positions,
            your_position=your_pos,
            best_competitor_position=best_competitor,
            position_gap=position_gap
        ))

    # Calculate averages
    avg_your_pos = None
    avg_competitor_pos = None
    if summary_stats["your_positions"]:
        avg_your_pos = sum(summary_stats["your_positions"]) / len(summary_stats["your_positions"])
    if summary_stats["competitor_positions"]:
        avg_competitor_pos = sum(summary_stats["competitor_positions"]) / len(summary_stats["competitor_positions"])

    summary = CompetitorComparisonSummary(
        total_regions=summary_stats["total_regions"],
        regions_with_your_data=summary_stats["regions_with_your_data"],
        winning_regions=summary_stats["winning_regions"],
        losing_regions=summary_stats["losing_regions"],
        tied_regions=summary_stats["tied_regions"],
        not_ranking_regions=summary_stats["not_ranking_regions"],
        avg_position=round(avg_your_pos, 1) if avg_your_pos else None,
        avg_competitor_position=round(avg_competitor_pos, 1) if avg_competitor_pos else None
    )

    logger.info(f"📤 GET /geoint/competitor-comparison/{keyword_id} - returning {len(regions)} regions")

    response = CompetitorComparisonResponse(
        keyword_id=keyword_id,
        keyword=keyword.keyword,
        user_domain=user_domain,
        competitors=competitor_domains,
        regions=regions,
        summary=summary
    )

    # Save comparison to history
    try:
        from app.models.competitor import CompetitorComparisonHistory
        history_entry = CompetitorComparisonHistory(
            user_id=current_user["id"],
            keyword_id=keyword_id,
            user_domain=user_domain,
            competitor_domains=list(competitor_domains),
            region_type=region_type,
            results=[r.model_dump() for r in regions],
            summary=summary.model_dump(),
        )
        db.add(history_entry)
        await db.flush()
        logger.info(f"💾 Saved comparison history: {history_entry.id}")
    except Exception as e:
        logger.warning(f"Failed to save comparison history: {e}")

    return response


# ============================================
# Competitor Comparison History Endpoints
# ============================================

@router.get("/competitor-comparisons/{keyword_id}/history", response_model=ComparisonHistoryListResponse)
async def get_comparison_history(
    keyword_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get list of historical competitor comparisons for a keyword."""
    from app.models.competitor import CompetitorComparisonHistory

    result = await db.execute(
        select(CompetitorComparisonHistory)
        .where(
            CompetitorComparisonHistory.user_id == current_user["id"],
            CompetitorComparisonHistory.keyword_id == keyword_id,
        )
        .order_by(CompetitorComparisonHistory.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    comparisons = []
    for row in rows:
        comparisons.append(ComparisonHistoryItem(
            id=str(row.id),
            user_domain=row.user_domain,
            competitor_domains=row.competitor_domains,
            region_type=row.region_type,
            summary=CompetitorComparisonSummary(**row.summary),
            created_at=row.created_at.isoformat(),
        ))

    return ComparisonHistoryListResponse(
        keyword_id=keyword_id,
        comparisons=comparisons,
    )


@router.get("/competitor-comparisons/history/{comparison_id}", response_model=CompetitorComparisonResponse)
async def get_comparison_by_id(
    comparison_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a specific historical competitor comparison by ID."""
    from app.models.competitor import CompetitorComparisonHistory

    result = await db.execute(
        select(CompetitorComparisonHistory)
        .where(
            CompetitorComparisonHistory.id == comparison_id,
            CompetitorComparisonHistory.user_id == current_user["id"],
        )
    )
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Comparison not found")

    # Get keyword name
    kw = await db.get(Keyword, str(row.keyword_id))
    keyword_name = kw.keyword if kw else "Unknown"

    regions = [RegionCompetitorData(**r) for r in row.results]

    return CompetitorComparisonResponse(
        keyword_id=str(row.keyword_id),
        keyword=keyword_name,
        user_domain=row.user_domain,
        competitors=row.competitor_domains,
        regions=regions,
        summary=CompetitorComparisonSummary(**row.summary),
    )


# ============================================
# TKGM (Turkish Land Registry) Endpoints
# ============================================

@router.get("/tkgm/provinces")
async def get_tkgm_provinces():
    """
    Get official list of Turkish provinces from TKGM

    Returns administrative boundary data from Turkish Land Registry.
    Useful for validating geographic data.
    """
    from app.services.external import TKGMClient

    async with TKGMClient() as client:
        try:
            provinces = await client.get_provinces()
            logger.info(f"✅ GET /geoint/tkgm/provinces - fetched {len(provinces)} provinces")
            return {
                "success": True,
                "count": len(provinces),
                "data": provinces
            }
        except Exception as e:
            logger.error(f"❌ Error fetching TKGM provinces: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch provinces from TKGM: {str(e)}"
            )


@router.get("/tkgm/districts/{province_id}")
async def get_tkgm_districts(province_id: int):
    """
    Get official list of districts for a province from TKGM

    Args:
        province_id: Province ID (e.g., 34 for Istanbul)

    Returns administrative district data from Turkish Land Registry.
    """
    from app.services.external import TKGMClient

    async with TKGMClient() as client:
        try:
            districts = await client.get_districts(province_id)
            logger.info(f"✅ GET /geoint/tkgm/districts/{province_id} - fetched {len(districts)} districts")
            return {
                "success": True,
                "province_id": province_id,
                "count": len(districts),
                "data": districts
            }
        except Exception as e:
            logger.error(f"❌ Error fetching TKGM districts for province {province_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch districts from TKGM: {str(e)}"
            )


@router.get("/tkgm/neighborhoods/{district_id}")
async def get_tkgm_neighborhoods(district_id: int):
    """
    Get official list of neighborhoods for a district from TKGM

    Args:
        district_id: District ID

    Returns administrative neighborhood data from Turkish Land Registry.
    """
    from app.services.external import TKGMClient

    async with TKGMClient() as client:
        try:
            neighborhoods = await client.get_neighborhoods(district_id)
            logger.info(f"✅ GET /geoint/tkgm/neighborhoods/{district_id} - fetched {len(neighborhoods)} neighborhoods")
            return {
                "success": True,
                "district_id": district_id,
                "count": len(neighborhoods),
                "data": neighborhoods
            }
        except Exception as e:
            logger.error(f"❌ Error fetching TKGM neighborhoods for district {district_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch neighborhoods from TKGM: {str(e)}"
            )


@router.get("/tkgm/search/district")
async def search_tkgm_district(
    name: str = Query(..., description="District name to search"),
    province_id: Optional[int] = Query(None, description="Filter by province ID")
):
    """
    Search for districts by name across TKGM data

    Args:
        name: District name (partial match supported)
        province_id: Optional province filter

    Returns matching districts from Turkish Land Registry.
    """
    from app.services.external import TKGMClient

    async with TKGMClient() as client:
        try:
            matches = await client.search_district(name, province_id)
            logger.info(f"✅ GET /geoint/tkgm/search/district?name={name} - found {len(matches)} matches")
            return {
                "success": True,
                "query": name,
                "province_id": province_id,
                "count": len(matches),
                "data": matches
            }
        except Exception as e:
            logger.error(f"❌ Error searching TKGM districts: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to search districts in TKGM: {str(e)}"
            )
