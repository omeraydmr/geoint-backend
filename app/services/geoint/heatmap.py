"""
Heatmap Generator for GEOINT visualization

Converts GEOINT scores to GeoJSON format for map display
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shapely import wkb
from shapely.geometry import mapping
import json

from app.models.geo import Province, District, Neighborhood, GEOINTScore, RegionType


class HeatmapGenerator:
    """
    Generate heatmap data from GEOINT scores

    Outputs GeoJSON FeatureCollections compatible with Mapbox GL JS
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_province_heatmap(
        self,
        keyword_id: str,
        include_geometry: bool = True
    ) -> Dict[str, Any]:
        """
        Generate province-level heatmap for a keyword

        Args:
            keyword_id: UUID of the keyword
            include_geometry: Include polygon geometry (True) or just centroids (False)

        Returns:
            GeoJSON FeatureCollection
        """
        # Get all provinces
        provinces_result = await self.db.execute(select(Province))
        provinces = {str(p.id): p for p in provinces_result.scalars().all()}

        # Get GEOINT scores for this keyword
        # Added ordering by calculated_at desc to get the most recent score if duplicates exist
        scores_result = await self.db.execute(
            select(GEOINTScore).where(
                GEOINTScore.keyword_id == keyword_id,
                GEOINTScore.region_type == RegionType.PROVINCE
            ).order_by(GEOINTScore.calculated_at.desc())
        )
        # Use a dict to store the most recent score for each region
        scores = {}
        for s in scores_result.scalars().all():
            reg_id_str = str(s.region_id)
            if reg_id_str not in scores:
                scores[reg_id_str] = s

        # Build GeoJSON features
        features = []
        for province_id, province in provinces.items():
            score_data = scores.get(province_id)

            # Geometry
            if include_geometry:
                geometry = self._to_geojson(province.geom)
            else:
                geometry = self._to_geojson(province.centroid)

            # Properties
            properties = {
                "id": province_id,
                "code": province.code,
                "name": province.name,
                "region": province.region,
                "population": province.population,
                "geoint_score": score_data.geoint_score if score_data else 0,
                "search_index": score_data.search_index if score_data else 0,
                "trend_score": score_data.trend_score if score_data else 0,
                "trend_direction": score_data.trend_direction if score_data else "stable",
                "has_data": score_data is not None
            }

            features.append({
                "type": "Feature",
                "id": province_id,
                "properties": properties,
                "geometry": geometry
            })

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "keyword_id": keyword_id,
                "region_type": "province",
                "total_regions": len(provinces),
                "regions_with_data": len(scores)
            }
        }

    async def generate_district_heatmap(
        self,
        keyword_id: str,
        province_id: Optional[str] = None,
        include_geometry: bool = True
    ) -> Dict[str, Any]:
        """
        Generate district-level heatmap

        Args:
            keyword_id: UUID of the keyword
            province_id: Filter by province - can be UUID or province code (e.g., "34" for Istanbul)
            include_geometry: Include polygon geometry

        Returns:
            GeoJSON FeatureCollection
        """
        import logging
        logger = logging.getLogger(__name__)

        # Get districts
        query = select(District)
        actual_province_uuid = None
        resolved_province_code = None
        resolved_province_name = None

        if province_id:
            # Check if province_id is a province code (2-digit string) or UUID
            if len(province_id) <= 2:
                # It's a province code, look up the actual province UUID
                province_code = province_id.zfill(2)
                logger.info(f"Looking up province by code: {province_code}")
                province_result = await self.db.execute(
                    select(Province).where(Province.code == province_code)
                )
                province = province_result.scalar_one_or_none()
                if province:
                    actual_province_uuid = province.id
                    resolved_province_code = province.code
                    resolved_province_name = province.name
                    logger.info(f"Found province: {province.name} (UUID: {province.id})")
                    query = query.where(District.province_id == province.id)
                else:
                    logger.warning(f"Province not found for code: {province_code}")
                    # Return empty result if province not found
                    return {
                        "type": "FeatureCollection",
                        "features": [],
                        "metadata": {
                            "keyword_id": keyword_id,
                            "region_type": "district",
                            "province_id": province_id,
                            "error": f"Province not found for code: {province_code}"
                        }
                    }
            else:
                # Assume it's a UUID
                actual_province_uuid = province_id
                query = query.where(District.province_id == province_id)
                # Resolve province code and name for metadata
                province_result = await self.db.execute(
                    select(Province).where(Province.id == province_id)
                )
                province = province_result.scalar_one_or_none()
                if province:
                    resolved_province_code = province.code
                    resolved_province_name = province.name

        districts_result = await self.db.execute(query)
        districts = {str(d.id): d for d in districts_result.scalars().all()}

        logger.info(f"Found {len(districts)} districts for province_id={province_id}")

        # Check if districts have geometry
        districts_with_geom = sum(1 for d in districts.values() if d.geom is not None)
        districts_with_centroid = sum(1 for d in districts.values() if d.centroid is not None)
        logger.info(f"Districts with geometry: {districts_with_geom}, with centroid: {districts_with_centroid}")

        # Get GEOINT scores
        scores_result = await self.db.execute(
            select(GEOINTScore).where(
                GEOINTScore.keyword_id == keyword_id,
                GEOINTScore.region_type == RegionType.DISTRICT
            ).order_by(GEOINTScore.calculated_at.desc())
        )
        scores = {}
        for s in scores_result.scalars().all():
            reg_id_str = str(s.region_id)
            if reg_id_str not in scores:
                scores[reg_id_str] = s

        # Build features
        features = []
        for district_id, district in districts.items():
            score_data = scores.get(district_id)

            geometry = self._to_geojson(
                district.geom if include_geometry else district.centroid
            )

            properties = {
                "id": district_id,
                "code": district.code,
                "name": district.name,
                "province_id": str(district.province_id),
                "population": district.population,
                "geoint_score": score_data.geoint_score if score_data else 0,
                "search_index": score_data.search_index if score_data else 0,
                "trend_direction": score_data.trend_direction if score_data else "stable",
                "has_data": score_data is not None
            }

            features.append({
                "type": "Feature",
                "id": district_id,
                "properties": properties,
                "geometry": geometry
            })

        # Log feature stats
        features_with_geometry = sum(1 for f in features if f.get("geometry") is not None)
        features_with_polygon = sum(1 for f in features if f.get("geometry", {}).get("type") in ["Polygon", "MultiPolygon"])
        features_with_score = sum(1 for f in features if f.get("properties", {}).get("geoint_score", 0) > 0)
        logger.info(f"Built {len(features)} features: {features_with_geometry} with geometry, {features_with_polygon} with polygon, {features_with_score} with score > 0")

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "keyword_id": keyword_id,
                "region_type": "district",
                "province_id": province_id,
                "province_code": resolved_province_code,
                "province_name": resolved_province_name,
                "total_regions": len(districts),
                "regions_with_data": len(scores),
                "features_with_geometry": features_with_geometry,
                "features_with_polygon": features_with_polygon
            }
        }

    async def generate_top_regions_list(
        self,
        keyword_id: str,
        region_type: RegionType,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top regions by GEOINT score

        Args:
            keyword_id: UUID of the keyword
            region_type: Type of region
            limit: Number of top regions

        Returns:
            List of region summaries
        """
        # Get top scores
        scores_result = await self.db.execute(
            select(GEOINTScore)
            .where(
                GEOINTScore.keyword_id == keyword_id,
                GEOINTScore.region_type == region_type
            )
            .order_by(GEOINTScore.geoint_score.desc())
            .limit(limit)
        )
        scores = scores_result.scalars().all()

        # Get region details
        results = []
        for score in scores:
            # Get region name based on type (pass raw_data for mock data support)
            region_name = await self._get_region_name(score.region_id, region_type, score.raw_data)

            results.append({
                "region_id": str(score.region_id),
                "region_name": region_name,
                "region_type": region_type.value,
                "geoint_score": score.geoint_score,
                "search_index": score.search_index,
                "trend_score": score.trend_score,
                "demographic_fit": score.demographic_fit,
                "competition_gap": score.competition_gap,
                "trend_direction": score.trend_direction,
                "calculated_at": score.calculated_at.isoformat() if score.calculated_at else None
            })

        return results

    def _to_geojson(self, geom) -> Dict:
        """Convert PostGIS geometry to GeoJSON"""
        if geom is None:
            return None

        # Convert WKB to Shapely geometry
        shape = wkb.loads(bytes(geom.data))

        # Convert to GeoJSON dict
        return mapping(shape)

    async def _get_region_name(self, region_id: str, region_type: RegionType, raw_data: dict = None) -> str:
        """Get region name by ID and type"""
        # Check if region_name is in raw_data (added in newer calculations)
        if raw_data and raw_data.get('region_name'):
            return raw_data['region_name']

        # Check if this is mock data with province_name in raw_data
        if raw_data and raw_data.get('mock') and raw_data.get('province_name'):
            return raw_data['province_name']

        if region_type == RegionType.PROVINCE:
            result = await self.db.execute(
                select(Province.name).where(Province.id == region_id)
            )
            name = result.scalar_one_or_none()
        elif region_type == RegionType.DISTRICT:
            result = await self.db.execute(
                select(District.name).where(District.id == region_id)
            )
            name = result.scalar_one_or_none()
        else:  # NEIGHBORHOOD
            result = await self.db.execute(
                select(Neighborhood.name).where(Neighborhood.id == region_id)
            )
            name = result.scalar_one_or_none()

        return name or "Unknown"

    async def generate_budget_recommendation(
        self,
        keyword_id: str,
        total_budget: float,
        region_type: RegionType = RegionType.PROVINCE,
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate budget allocation recommendations based on GEOINT scores

        Args:
            keyword_id: UUID of the keyword
            total_budget: Total budget to allocate (TL)
            region_type: Type of regions to allocate to
            top_n: Number of top regions to consider

        Returns:
            List of budget allocations
        """
        # Get top regions
        top_regions = await self.generate_top_regions_list(keyword_id, region_type, top_n)

        if not top_regions:
            return []

        # Calculate total score for normalization
        total_score = sum(r['geoint_score'] for r in top_regions)

        # Allocate budget proportionally to scores
        allocations = []
        for region in top_regions:
            allocation_pct = (region['geoint_score'] / total_score) * 100
            allocated_budget = (region['geoint_score'] / total_score) * total_budget

            allocations.append({
                **region,
                "allocated_budget": round(allocated_budget, 2),
                "allocation_percentage": round(allocation_pct, 2),
                "recommended_channels": self._get_recommended_channels(region)
            })

        return allocations

    def _get_recommended_channels(self, region: Dict) -> List[str]:
        """Get recommended marketing channels based on region characteristics"""
        channels = []

        # High search index -> SEO/SEM
        if region['search_index'] > 70:
            channels.append("Google Ads")
            channels.append("SEO")

        # Growing trend -> Social media
        if region['trend_direction'] == 'up':
            channels.append("Social Media Ads")

        # Good demographic fit -> Display ads
        if region['demographic_fit'] > 60:
            channels.append("Display Advertising")

        # Low competition -> Organic content
        if region['competition_gap'] > 70:
            channels.append("Content Marketing")

        return channels if channels else ["General Marketing"]
