"""Auto-seed geographic data on startup from bundled static GeoJSON files.

Reads Turkey's ADM1 (provinces) and ADM2 (districts) boundaries from local
GeoJSON files stored in ``backend/data/``.  These files are a complete,
authoritative snapshot of all 81 provinces and 973 districts -- no external
API calls are made, ensuring deterministic, offline-capable seeding.

Province-district relationships are established via spatial containment:
each district's centroid is tested against province polygons to find its
parent.  A nearest-centroid fallback handles edge cases caused by
simplified boundaries.
"""
import json
import logging
import pathlib
import uuid
from datetime import datetime

from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon, Polygon, shape
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.geo import District, GEOINTScore, Province, RegionType

logger = logging.getLogger(__name__)

_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
_ADM1_PATH = _DATA_DIR / "turkey_adm1.geojson"
_ADM2_PATH = _DATA_DIR / "turkey_adm2.geojson"

# Region mapping by province plate code (1-81).
REGION_MAP: dict[int, str] = {
    1: "Akdeniz", 2: "Güneydoğu Anadolu", 3: "Ege", 4: "Doğu Anadolu",
    5: "Karadeniz", 6: "İç Anadolu", 7: "Akdeniz", 8: "Karadeniz",
    9: "Ege", 10: "Marmara", 11: "Marmara", 12: "Doğu Anadolu",
    13: "Doğu Anadolu", 14: "Karadeniz", 15: "Akdeniz", 16: "Marmara",
    17: "Marmara", 18: "İç Anadolu", 19: "Karadeniz", 20: "Ege",
    21: "Güneydoğu Anadolu", 22: "Marmara", 23: "Doğu Anadolu",
    24: "Doğu Anadolu", 25: "Doğu Anadolu", 26: "İç Anadolu",
    27: "Güneydoğu Anadolu", 28: "Karadeniz", 29: "Karadeniz",
    30: "Doğu Anadolu", 31: "Akdeniz", 32: "Akdeniz", 33: "Akdeniz",
    34: "Marmara", 35: "Ege", 36: "Doğu Anadolu", 37: "Karadeniz",
    38: "İç Anadolu", 39: "Marmara", 40: "İç Anadolu", 41: "Marmara",
    42: "İç Anadolu", 43: "Ege", 44: "Doğu Anadolu", 45: "Ege",
    46: "Akdeniz", 47: "Güneydoğu Anadolu", 48: "Ege",
    49: "Doğu Anadolu", 50: "İç Anadolu", 51: "İç Anadolu",
    52: "Karadeniz", 53: "Karadeniz", 54: "Marmara", 55: "Karadeniz",
    56: "Güneydoğu Anadolu", 57: "Karadeniz", 58: "İç Anadolu",
    59: "Marmara", 60: "Karadeniz", 61: "Karadeniz",
    62: "Doğu Anadolu", 63: "Güneydoğu Anadolu", 64: "Ege",
    65: "Doğu Anadolu", 66: "İç Anadolu", 67: "Karadeniz",
    68: "İç Anadolu", 69: "Karadeniz", 70: "İç Anadolu",
    71: "İç Anadolu", 72: "Güneydoğu Anadolu", 73: "Güneydoğu Anadolu",
    74: "Karadeniz", 75: "Doğu Anadolu", 76: "Doğu Anadolu",
    77: "Marmara", 78: "Karadeniz", 79: "Güneydoğu Anadolu",
    80: "Akdeniz", 81: "Karadeniz",
}


def _load_geojson(path: pathlib.Path) -> dict:
    """Load a GeoJSON file from the local filesystem."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _ensure_multipolygon(geom_shape) -> MultiPolygon:
    """Normalise any polygon-family geometry to a valid MultiPolygon."""
    if not geom_shape.is_valid:
        geom_shape = geom_shape.buffer(0)
    if isinstance(geom_shape, Polygon):
        return MultiPolygon([geom_shape])
    return geom_shape


def _build_province_spatial_index(
    provinces: list[Province],
    province_shapes: dict[str, object],
) -> list[tuple[Province, object]]:
    """Return a list of (Province, shapely_geometry) pairs for spatial lookup."""
    return [(p, province_shapes[p.code]) for p in provinces if p.code in province_shapes]


async def _seed_provinces(db: AsyncSession) -> dict[str, Province]:
    """Insert all 81 provinces from the local ADM1 GeoJSON.

    Returns a mapping of ``{plate_code: Province}`` for downstream
    district matching.
    """
    data = _load_geojson(_ADM1_PATH)
    features = data.get("features", [])
    logger.info("Loading %d province features from %s.", len(features), _ADM1_PATH.name)

    now = datetime.utcnow()
    province_map: dict[str, Province] = {}

    for feature in features:
        props = feature["properties"]
        name = props.get("shapeName")
        iso = props.get("shapeISO", "")

        if not name or not iso:
            continue

        try:
            code = iso.split("-")[1]
        except (IndexError, ValueError):
            logger.warning("Skipping province with invalid ISO: %s", iso)
            continue

        geom = _ensure_multipolygon(shape(feature["geometry"]))
        centroid = geom.centroid
        region = REGION_MAP.get(int(code), "Unknown")

        province = Province(
            id=uuid.uuid4(),
            code=code,
            name=name,
            region=region,
            population=0,
            area_km2=round(geom.area * 12321.0, 2),
            geom=from_shape(geom, srid=4326),
            centroid=from_shape(centroid, srid=4326),
            created_at=now,
            updated_at=now,
        )
        db.add(province)
        province_map[code] = province

    await db.flush()
    logger.info("Inserted %d provinces.", len(province_map))
    return province_map


async def _seed_districts(
    db: AsyncSession,
    province_map: dict[str, Province],
) -> int:
    """Insert all 973 districts from the local ADM2 GeoJSON.

    Each district is matched to its parent province using spatial
    containment (centroid-in-polygon).  When simplified boundaries cause
    a centroid to fall outside every province, the nearest-centroid
    fallback assigns the district to the closest province.
    """
    data = _load_geojson(_ADM2_PATH)
    features = data.get("features", [])
    logger.info("Loading %d district features from %s.", len(features), _ADM2_PATH.name)

    # Build shapely geometries for province matching.
    province_shapes: dict[str, object] = {}
    for feature in _load_geojson(_ADM1_PATH).get("features", []):
        iso = feature["properties"].get("shapeISO", "")
        if iso:
            code = iso.split("-")[1]
            province_shapes[code] = _ensure_multipolygon(shape(feature["geometry"]))

    spatial_index = _build_province_spatial_index(
        list(province_map.values()), province_shapes
    )

    now = datetime.utcnow()
    created = 0
    spatial_matches = 0
    nearest_matches = 0
    district_counter: dict[str, int] = {}

    for feature in features:
        props = feature["properties"]
        name = props.get("shapeName")
        if not name:
            continue

        try:
            geom = _ensure_multipolygon(shape(feature["geometry"]))
        except Exception:
            logger.warning("Skipping district '%s': invalid geometry.", name)
            continue

        centroid = geom.centroid

        # Strategy 1: spatial containment (primary).
        matched_province = None
        for province, p_shape in spatial_index:
            if p_shape.contains(centroid):
                matched_province = province
                spatial_matches += 1
                break

        # Strategy 2: nearest centroid fallback.
        if matched_province is None:
            best_distance = float("inf")
            for province, p_shape in spatial_index:
                dist = p_shape.centroid.distance(centroid)
                if dist < best_distance:
                    best_distance = dist
                    matched_province = province
            if matched_province is not None:
                nearest_matches += 1
                logger.debug(
                    "District '%s' matched to '%s' via nearest centroid (d=%.4f).",
                    name, matched_province.name, best_distance,
                )

        if matched_province is None:
            logger.warning("District '%s' could not be matched to any province.", name)
            continue

        # Generate a deterministic, unique district code.
        pcode = matched_province.code
        district_counter[pcode] = district_counter.get(pcode, 0) + 1
        code = f"{pcode}-{district_counter[pcode]:03d}"

        district = District(
            id=uuid.uuid4(),
            province_id=matched_province.id,
            code=code,
            name=name,
            population=0,
            area_km2=round(geom.area * 12321.0, 2),
            geom=from_shape(geom, srid=4326),
            centroid=from_shape(centroid, srid=4326),
            created_at=now,
            updated_at=now,
        )
        db.add(district)
        created += 1

        if created % 200 == 0:
            await db.flush()

    await db.flush()
    logger.info(
        "Inserted %d districts (spatial=%d, nearest=%d).",
        created, spatial_matches, nearest_matches,
    )
    return created


async def seed_geographic_data() -> None:
    """Seed provinces and districts from bundled static GeoJSON files.

    Safe to call on every startup.  Behaviour:
    - No provinces in DB  -> full seed (provinces + districts).
    - Provinces exist but district count is low (<900) -> reseed districts.
    - Data looks healthy   -> skip (no-op).
    """
    if not _ADM1_PATH.exists():
        logger.error("Province GeoJSON not found at %s. Seeding aborted.", _ADM1_PATH)
        return
    if not _ADM2_PATH.exists():
        logger.error("District GeoJSON not found at %s. Seeding aborted.", _ADM2_PATH)
        return

    async with AsyncSessionLocal() as db:
        province_count = (await db.execute(select(func.count(Province.id)))).scalar()
        district_count = (await db.execute(select(func.count(District.id)))).scalar()

        if province_count >= 81 and district_count >= 900:
            logger.info(
                "Geographic data already seeded (%d provinces, %d districts). Skipping.",
                province_count, district_count,
            )
            return

        needs_province_seed = province_count < 81
        needs_district_seed = district_count < 900

        if needs_province_seed:
            logger.info("Seeding provinces from local GeoJSON (%d found, need 81)...", province_count)
            # Clear existing partial data to avoid duplicates.
            if province_count > 0:
                await db.execute(delete(GEOINTScore).where(GEOINTScore.region_type == RegionType.DISTRICT))
                await db.execute(delete(District))
                await db.execute(delete(GEOINTScore).where(GEOINTScore.region_type == RegionType.PROVINCE))
                await db.execute(delete(Province))
                await db.flush()
                needs_district_seed = True

            province_map = await _seed_provinces(db)
        else:
            # Load existing provinces for district matching.
            result = await db.execute(select(Province))
            province_map = {p.code: p for p in result.scalars().all()}

        if needs_district_seed:
            logger.info("Seeding districts from local GeoJSON (%d found, need ~973)...", district_count)
            if district_count > 0 and not needs_province_seed:
                await db.execute(delete(GEOINTScore).where(GEOINTScore.region_type == RegionType.DISTRICT))
                await db.execute(delete(District))
                await db.flush()

            district_count = await _seed_districts(db, province_map)

        await db.commit()

        final_p = (await db.execute(select(func.count(Province.id)))).scalar()
        final_d = (await db.execute(select(func.count(District.id)))).scalar()
        logger.info(
            "Geographic seeding complete: %d provinces, %d districts.",
            final_p, final_d,
        )
