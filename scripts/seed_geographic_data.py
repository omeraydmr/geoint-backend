#!/usr/bin/env python3
"""
Seed Geographic Data for Turkey

Populates provinces and districts from TKGM (Turkish Land Registry) API
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.geo import Province, District
from app.services.external.tkgm import TKGMClient
import logging
import uuid
from datetime import datetime
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, Polygon, MultiPolygon

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_provinces(db: AsyncSession):
    """Seed provinces from TKGM API"""
    logger.info("🌍 Fetching provinces from TKGM API...")

    async with TKGMClient() as client:
        provinces_data = await client.get_provinces()

    logger.info(f"📦 Received {len(provinces_data)} provinces from TKGM")

    # Map of Turkish regions by province code
    regions_map = {
        # Marmara
        range(34, 35): "Marmara", range(6, 7): "Marmara", range(10, 11): "Marmara",
        range(11, 12): "Marmara", range(16, 17): "Marmara", range(17, 18): "Marmara",
        range(39, 40): "Marmara", range(41, 42): "Marmara", range(43, 44): "Marmara",
        range(54, 55): "Marmara", range(59, 60): "Marmara", range(77, 78): "Marmara",

        # Ege (Aegean)
        range(3, 4): "Ege", range(9, 10): "Ege", range(20, 21): "Ege",
        range(35, 36): "Ege", range(45, 46): "Ege", range(48, 49): "Ege",
        range(64, 65): "Ege", range(83, 84): "Ege",

        # Akdeniz (Mediterranean)
        range(1, 2): "Akdeniz", range(7, 8): "Akdeniz", range(15, 16): "Akdeniz",
        range(31, 32): "Akdeniz", range(32, 33): "Akdeniz", range(33, 34): "Akdeniz",
        range(46, 47): "Akdeniz", range(80, 81): "Akdeniz",

        # İç Anadolu (Central Anatolia)
        range(5, 6): "İç Anadolu", range(18, 19): "İç Anadolu", range(19, 20): "İç Anadolu",
        range(38, 39): "İç Anadolu", range(40, 41): "İç Anadolu", range(42, 43): "İç Anadolu",
        range(50, 51): "İç Anadolu", range(51, 52): "İç Anadolu", range(66, 67): "İç Anadolu",
        range(68, 69): "İç Anadolu", range(70, 71): "İç Anadolu", range(71, 72): "İç Anadolu",
        range(76, 77): "İç Anadolu",

        # Karadeniz (Black Sea)
        range(8, 9): "Karadeniz", range(37, 38): "Karadeniz", range(55, 56): "Karadeniz",
        range(57, 58): "Karadeniz", range(60, 61): "Karadeniz", range(61, 62): "Karadeniz",
        range(67, 68): "Karadeniz", range(74, 75): "Karadeniz", range(78, 79): "Karadeniz",
        range(81, 82): "Karadeniz",

        # Doğu Anadolu (Eastern Anatolia)
        range(4, 5): "Doğu Anadolu", range(12, 13): "Doğu Anadolu", range(13, 14): "Doğu Anadolu",
        range(23, 24): "Doğu Anadolu", range(24, 25): "Doğu Anadolu", range(25, 26): "Doğu Anadolu",
        range(36, 37): "Doğu Anadolu", range(49, 50): "Doğu Anadolu", range(65, 66): "Doğu Anadolu",

        # Güneydoğu Anadolu (Southeastern Anatolia)
        range(2, 3): "Güneydoğu Anadolu", range(21, 22): "Güneydoğu Anadolu", range(27, 28): "Güneydoğu Anadolu",
        range(56, 57): "Güneydoğu Anadolu", range(62, 63): "Güneydoğu Anadolu", range(63, 64): "Güneydoğu Anadolu",
        range(72, 73): "Güneydoğu Anadolu", range(73, 74): "Güneydoğu Anadolu", range(79, 80): "Güneydoğu Anadolu",
    }

    def get_region(code: int) -> str:
        """Get region name by province code"""
        for code_range, region in regions_map.items():
            if code in code_range:
                return region
        return "Unknown"

    provinces_created = 0
    provinces_updated = 0

    for province_data in provinces_data:
        # Extract province info from TKGM response
        # The response structure varies, handle both formats
        if isinstance(province_data, dict):
            if 'properties' in province_data:
                # GeoJSON format
                props = province_data['properties']
                code = str(props.get('il_kodu') or props.get('IL_KODU', '')).zfill(2)
                name = props.get('il_adi') or props.get('IL_ADI', '')

                # Get geometry
                geom_data = province_data.get('geometry')
                if geom_data:
                    # Create a simple point for centroid
                    # In production, you'd parse the actual geometry
                    centroid_geom = from_shape(Point(35.0, 39.0), srid=4326)
                    province_geom = from_shape(MultiPolygon([Polygon([(34, 38), (36, 38), (36, 40), (34, 40), (34, 38)])]), srid=4326)
                else:
                    centroid_geom = from_shape(Point(35.0, 39.0), srid=4326)
                    province_geom = from_shape(MultiPolygon([Polygon([(34, 38), (36, 38), (36, 40), (34, 40), (34, 38)])]), srid=4326)
            else:
                # Direct object format
                code = str(province_data.get('il_kodu') or province_data.get('id', '')).zfill(2)
                name = province_data.get('il_adi') or province_data.get('name', '')
                centroid_geom = from_shape(Point(35.0, 39.0), srid=4326)
                province_geom = from_shape(MultiPolygon([Polygon([(34, 38), (36, 38), (36, 40), (34, 40), (34, 38)])]), srid=4326)
        else:
            continue

        if not code or not name:
            continue

        region = get_region(int(code))

        # Check if province exists
        result = await db.execute(
            select(Province).where(Province.code == code)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update
            existing.name = name
            existing.region = region
            existing.updated_at = datetime.utcnow()
            provinces_updated += 1
        else:
            # Create new
            province = Province(
                id=uuid.uuid4(),
                code=code,
                name=name,
                region=region,
                population=0,  # Will be updated separately
                area_km2=0.0,
                geom=province_geom,
                centroid=centroid_geom,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(province)
            provinces_created += 1

    await db.commit()
    logger.info(f"✅ Provinces: {provinces_created} created, {provinces_updated} updated")
    return provinces_created, provinces_updated


async def seed_districts(db: AsyncSession):
    """Seed districts from TKGM API"""
    logger.info("🌍 Fetching districts from TKGM API...")

    # Get all provinces first
    result = await db.execute(select(Province))
    provinces = {p.code: p for p in result.scalars().all()}

    if not provinces:
        logger.error("❌ No provinces found! Run province seeding first.")
        return 0, 0

    async with TKGMClient() as client:
        all_districts = await client.get_all_districts()

    logger.info(f"📦 Received {len(all_districts)} districts from TKGM")

    districts_created = 0
    districts_updated = 0

    for district_data in all_districts:
        # Extract district info
        if isinstance(district_data, dict):
            if 'properties' in district_data:
                props = district_data['properties']
                province_code = str(props.get('il_kodu') or props.get('IL_KODU', '')).zfill(2)
                district_code = str(props.get('ilce_kodu') or props.get('ILCE_KODU', ''))
                district_name = props.get('ilce_adi') or props.get('ILCE_ADI', '')
            else:
                province_code = str(district_data.get('il_kodu') or district_data.get('il_id', '')).zfill(2)
                district_code = str(district_data.get('ilce_kodu') or district_data.get('id', ''))
                district_name = district_data.get('ilce_adi') or district_data.get('name', '')
        else:
            continue

        if not district_code or not district_name or province_code not in provinces:
            continue

        province = provinces[province_code]

        # Create unique code
        unique_code = f"{province_code}{district_code}"

        # Check if district exists
        result = await db.execute(
            select(District).where(District.code == unique_code)
        )
        existing = result.scalar_one_or_none()

        # Simple centroid
        centroid_geom = from_shape(Point(35.0, 39.0), srid=4326)
        district_geom = from_shape(MultiPolygon([Polygon([(34.5, 38.5), (35.5, 38.5), (35.5, 39.5), (34.5, 39.5), (34.5, 38.5)])]), srid=4326)

        if existing:
            existing.name = district_name
            existing.province_id = province.id
            existing.updated_at = datetime.utcnow()
            districts_updated += 1
        else:
            district = District(
                id=uuid.uuid4(),
                province_id=province.id,
                code=unique_code,
                name=district_name,
                population=0,
                area_km2=0.0,
                geom=district_geom,
                centroid=centroid_geom,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(district)
            districts_created += 1

    await db.commit()
    logger.info(f"✅ Districts: {districts_created} created, {districts_updated} updated")
    return districts_created, districts_updated


async def main():
    """Main seeding function"""
    logger.info("=" * 60)
    logger.info("🚀 GEOINT Geographic Data Seeding")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as db:
        # Check current state
        province_count = await db.execute(select(func.count(Province.id)))
        district_count = await db.execute(select(func.count(District.id)))

        logger.info(f"📊 Current state:")
        logger.info(f"   Provinces: {province_count.scalar()}")
        logger.info(f"   Districts: {district_count.scalar()}")
        logger.info("")

        # Seed provinces
        try:
            p_created, p_updated = await seed_provinces(db)
            logger.info("")
        except Exception as e:
            logger.error(f"❌ Province seeding failed: {e}")
            import traceback
            traceback.print_exc()
            return

        # Seed districts
        try:
            d_created, d_updated = await seed_districts(db)
            logger.info("")
        except Exception as e:
            logger.error(f"❌ District seeding failed: {e}")
            import traceback
            traceback.print_exc()
            return

        # Final count
        province_count = await db.execute(select(func.count(Province.id)))
        district_count = await db.execute(select(func.count(District.id)))

        logger.info("=" * 60)
        logger.info("✅ SEEDING COMPLETED!")
        logger.info(f"   Provinces: {province_count.scalar()} total")
        logger.info(f"   Districts: {district_count.scalar()} total")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
