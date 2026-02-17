# STRATYON Database Documentation

SQL-based database schema for the STRATYON GEOINT Intelligence Platform.

## 📁 Directory Structure

```
database/
├── schema/
│   ├── 001_initial_schema.sql      # All tables and enums
│   ├── 002_spatial_indexes.sql     # GIST spatial indexes
│   └── 003_constraints.sql         # Foreign key constraints
├── seed/
│   └── (geographic data exports)
├── init_db.py                      # Python initialization script
└── README.md                       # This file
```

## 🚀 Quick Start

### Prerequisites

- PostgreSQL 13+
- PostGIS extension
- Python 3.9+ (for initialization script)

### Option 1: Initialize with SQL (Recommended)

```bash
# 1. Create database
createdb geoint_db

# 2. Run schema files in order
psql -d geoint_db -f schema/001_initial_schema.sql
psql -d geoint_db -f schema/002_spatial_indexes.sql
psql -d geoint_db -f schema/003_constraints.sql

# 3. Seed geographic data
cd ../..
python backend/scripts/seed_geographic_data.py
python backend/scripts/seed_turkey_provinces.py
```

### Option 2: Initialize with Python

```bash
# 1. Create database
createdb geoint_db

# 2. Enable PostGIS
psql -d geoint_db -c "CREATE EXTENSION postgis;"

# 3. Run initialization script
python backend/database/init_db.py

# 4. Seed data
python backend/scripts/seed_geographic_data.py
python backend/scripts/seed_turkey_provinces.py
```

## 📊 Database Schema

### Core Tables

| Table | Purpose | Records |
|-------|---------|---------|
| `users` | User accounts and subscriptions | ~Thousands |
| `refresh_tokens` | JWT token management | ~Thousands |
| `provinces` | Turkish provinces (İller) | 81 |
| `districts` | Turkish districts (İlçeler) | ~970 |
| `neighborhoods` | Turkish neighborhoods (Mahalleler) | ~50,000 |
| `keywords` | Tracked keywords | ~Thousands |
| `geoint_scores` | GEOINT scores by region | ~Millions |
| `competitors` | Competitor domains | ~Thousands |
| `strategies` | AI-generated strategies | ~Thousands |
| `media_mentions` | Media coverage | ~Thousands |

### Data Types

**Enums:**
- `subscription_plan`: free, insight, strategy, growth, enterprise
- `region_type`: il (province), ilce (district), mahalle (neighborhood)
- `strategy_status`: DRAFT, ACTIVE, PAUSED, COMPLETED, ARCHIVED
- `task_status`: TODO, IN_PROGRESS, COMPLETED, BLOCKED, CANCELLED
- `task_priority`: LOW, MEDIUM, HIGH, URGENT

**Geospatial:**
- All geographic tables use `GEOMETRY` with SRID 4326 (WGS84)
- GIST indexes for spatial queries

## 🔄 Migration Strategy

### Current Approach: SQL-First

The database uses **SQL files as source of truth**. SQLAlchemy models mirror the SQL schema for ORM convenience.

### Future: Liquibase Migration

When ready for production migrations, wrap SQL files in Liquibase changesets:

```xml
<!-- liquibase/changelog-master.xml -->
<databaseChangeLog>
  <changeSet id="001" author="stratyon">
    <sqlFile path="schema/001_initial_schema.sql"/>
  </changeSet>
  <changeSet id="002" author="stratyon">
    <sqlFile path="schema/002_spatial_indexes.sql"/>
  </changeSet>
  <changeSet id="003" author="stratyon">
    <sqlFile path="schema/003_constraints.sql"/>
  </changeSet>
</databaseChangeLog>
```

## 🗺️ Spatial Queries

The database supports PostGIS spatial operations:

```sql
-- Find province containing a point (Istanbul coordinates)
SELECT name FROM provinces
WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(28.9784, 41.0082), 4326));

-- Find all districts within 50km of a point
SELECT d.name, ST_Distance(d.centroid::geography, point::geography) / 1000 as distance_km
FROM districts d,
     ST_SetSRID(ST_MakePoint(28.9784, 41.0082), 4326) as point
WHERE ST_DWithin(d.centroid::geography, point::geography, 50000)
ORDER BY distance_km;

-- Calculate GEOINT scores for regions intersecting a bounding box
SELECT gs.*, p.name as region_name
FROM geoint_scores gs
JOIN provinces p ON gs.region_id = p.id
WHERE gs.region_type = 'il'
  AND ST_Intersects(p.geom, ST_MakeEnvelope(26, 39, 30, 42, 4326));
```

## 🔧 Maintenance

### Backup Database

```bash
pg_dump -Fc geoint_db > backup_$(date +%Y%m%d).dump
```

### Restore Database

```bash
pg_restore -d geoint_db backup_20260106.dump
```

### Drop and Recreate

```bash
dropdb geoint_db
createdb geoint_db
psql -d geoint_db -f schema/001_initial_schema.sql
psql -d geoint_db -f schema/002_spatial_indexes.sql
psql -d geoint_db -f schema/003_constraints.sql
```

## 📈 Performance

### Indexes

All critical queries are covered by indexes:
- **Spatial indexes (GIST)** on all geospatial columns
- **B-tree indexes** on foreign keys and frequently queried columns
- **Unique indexes** on tokens, emails, URLs
- **Composite indexes** for common query patterns

### Query Optimization

```sql
-- Always use spatial indexes for geographic queries
EXPLAIN ANALYZE
SELECT * FROM provinces
WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(28.9784, 41.0082), 4326));

-- Index usage for GEOINT score lookups
EXPLAIN ANALYZE
SELECT * FROM geoint_scores
WHERE keyword_id = 'some-uuid'
  AND region_type = 'il'
  AND region_id = 'some-uuid';
```

## 🔗 Related Documentation

- [Main README](../../README.md)
- [SQLAlchemy Models](../app/models/)
- [Seed Scripts](../scripts/)
- [API Documentation](../../docs/architecture/)

## 📝 Notes

- Schema version: 1.0
- Last updated: 2026-01-06
- No Alembic migrations (using SQL files)
- Liquibase-ready for future production migrations
