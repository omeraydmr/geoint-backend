#!/usr/bin/env python3
"""
Seed Real Geographic Data for Turkey

Fetches high-quality GeoJSON data for Turkey's provinces and districts
and updates the database with real geometries.
"""
import asyncio
import sys
import json
import logging
from pathlib import Path
import httpx
from shapely.geometry import shape, MultiPolygon, Polygon, Point
from geoalchemy2.shape import from_shape
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
import os

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent / '.env')

# Force IPv4 to avoid localhost resolution issues
os.environ["POSTGRES_HOST"] = "127.0.0.1"
# Override password with the one that actually works
os.environ["POSTGRES_PASSWORD"] = "postgres"

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.geo import Province, District
import uuid
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sources
PROVINCES_URL = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/TUR/ADM1/geoBoundaries-TUR-ADM1.geojson"
# New Districts source
DISTRICTS_URL = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/TUR/ADM2/geoBoundaries-TUR-ADM2.geojson"

async def fetch_geojson(url: str):
    logger.info(f"📥 Fetching GeoJSON from {url}...")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
        return response.json()

def fix_geometry(geom_shape):
    """Ensure geometry is MultiPolygon and valid"""
    if isinstance(geom_shape, Polygon):
        return MultiPolygon([geom_shape])
    elif isinstance(geom_shape, MultiPolygon):
        return geom_shape
    else:
        # Try buffer(0) to fix validity
        return geom_shape.buffer(0)

async def seed_provinces(db: AsyncSession):
    data = await fetch_geojson(PROVINCES_URL)
    features = data.get("features", [])
    logger.info(f"🌍 Found {len(features)} provinces in GeoJSON")

    updated = 0
    created = 0

    for feature in features:
        props = feature["properties"]
        
        name = props.get("shapeName")
        iso = props.get("shapeISO") # Format: TR-01
        
        if not name or not iso:
            continue
            
        # Extract code from ISO (TR-01 -> 01)
        try:
            code = iso.split("-")[1]
        except IndexError:
            logger.warning(f"⚠️ Invalid ISO code: {iso}")
            continue
            
        # Geometry
        geom = shape(feature["geometry"])
        if not geom.is_valid:
            geom = geom.buffer(0)
        
        if isinstance(geom, Polygon):
            geom = MultiPolygon([geom])
            
        centroid = geom.centroid
        
        # WKB Element
        wkb_geom = from_shape(geom, srid=4326)
        wkb_centroid = from_shape(centroid, srid=4326)

        # Upsert
        result = await db.execute(select(Province).where(Province.code == code))
        province = result.scalar_one_or_none()

        if province:
            province.name = name
            province.geom = wkb_geom
            province.centroid = wkb_centroid
            province.updated_at = datetime.utcnow()
            updated += 1
        else:
            # Region mapping (simplified)
            province = Province(
                id=uuid.uuid4(),
                code=code,
                name=name,
                region="Unknown",
                population=0,
                area_km2=0,
                geom=wkb_geom,
                centroid=wkb_centroid,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(province)
            created += 1
            
    await db.commit()
    logger.info(f"✅ Provinces: {updated} updated, {created} created")

async def seed_districts(db: AsyncSession):
    # Clear existing districts to remove mock data
    logger.info("🗑️ Deleting existing districts...")
    await db.execute(delete(District))
    await db.commit()

    data = await fetch_geojson(DISTRICTS_URL)
    features = data.get("features", [])
    logger.info(f"🌍 Found {len(features)} districts in GeoJSON")
    
    # Pre-fetch provinces with geometry for spatial join
    result = await db.execute(select(Province))
    provinces_db = result.scalars().all()
    
    # Convert to shapely objects
    from geoalchemy2.shape import to_shape
    provinces_shapes = []
    for p in provinces_db:
        if p.geom is not None:
            try:
                geom_shape = to_shape(p.geom)
                provinces_shapes.append((p, geom_shape))
            except Exception as e:
                logger.error(f"Error converting province {p.name} geometry: {e}")
    
    logger.info(f"Loaded {len(provinces_shapes)} provinces for spatial matching")
    
    updated = 0
    created = 0
    
    for i, feature in enumerate(features):
        if i % 100 == 0:
            logger.info(f"Processing district {i}/{len(features)}...")

        props = feature["properties"]
        name = props.get("shapeName")
        
        if not name:
            continue

        # Geometry
        try:
            geom = shape(feature["geometry"])
            if not geom.is_valid:
                geom = geom.buffer(0)
        except Exception as e:
            logger.warning(f"Invalid geometry for {name}: {e}")
            continue
            
        centroid = geom.centroid
        
        # Find province
        matched_province = None
        for p, p_shape in provinces_shapes:
            if p_shape.contains(centroid):
                matched_province = p
                break
        
        if not matched_province:
            # logger.warning(f"District {name} centroid not inside any province")
            continue

        # WKB
        if isinstance(geom, Polygon):
            geom = MultiPolygon([geom])
            
        wkb_geom = from_shape(geom, srid=4326)
        wkb_centroid = from_shape(centroid, srid=4326)
        
        # Upsert
        # Check by name and province
        result = await db.execute(select(District).where(
            District.name == name, 
            District.province_id == matched_province.id
        ))
        district = result.scalar_one_or_none()
        
        if district:
            district.geom = wkb_geom
            district.centroid = wkb_centroid
            district.updated_at = datetime.utcnow()
            updated += 1
        else:
            # Create new
            # Generate code: Province Code + Name Prefix + Random
            # Max 10 chars. Prov(2) + Name(3) + Rand(3) = 8 chars.
            code = f"{matched_province.code}{name[:3].upper()}{uuid.uuid4().hex[:3]}"
            
            district = District(
                id=uuid.uuid4(),
                province_id=matched_province.id,
                code=code,
                name=name,
                population=0, # Unknown
                area_km2=0,
                geom=wkb_geom,
                centroid=wkb_centroid,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(district)
            created += 1
    
    await db.commit()
    logger.info(f"✅ Districts: {updated} updated, {created} created")

async def main():
    async with AsyncSessionLocal() as db:
        await seed_provinces(db)
        # Districts might be huge and take time.
        # Uncomment to run district seeding
        await seed_districts(db)

if __name__ == "__main__":
    asyncio.run(main())
