-- =============================================
-- STRATYON Database - Spatial Indexes
-- =============================================
-- Version: 1.0
-- Created: 2026-01-06
--
-- GIST (Generalized Search Tree) indexes for
-- optimal spatial query performance
-- =============================================

-- =============================================
-- PROVINCES SPATIAL INDEXES
-- =============================================

-- Spatial index on province geometries
CREATE INDEX IF NOT EXISTS idx_provinces_geom_gist
ON provinces USING GIST(geom);

-- Spatial index on province centroids
CREATE INDEX IF NOT EXISTS idx_provinces_centroid_gist
ON provinces USING GIST(centroid);

-- Regular B-tree index on province code for fast lookups
CREATE INDEX IF NOT EXISTS idx_provinces_code
ON provinces(code);

-- =============================================
-- DISTRICTS SPATIAL INDEXES
-- =============================================

-- Spatial index on district geometries
CREATE INDEX IF NOT EXISTS idx_districts_geom_gist
ON districts USING GIST(geom);

-- Spatial index on district centroids
CREATE INDEX IF NOT EXISTS idx_districts_centroid_gist
ON districts USING GIST(centroid);

-- Regular indexes for relationships and lookups
CREATE INDEX IF NOT EXISTS idx_districts_province
ON districts(province_id);

CREATE INDEX IF NOT EXISTS idx_districts_code
ON districts(code);

-- =============================================
-- NEIGHBORHOODS SPATIAL INDEXES
-- =============================================

-- Spatial index on neighborhood geometries
CREATE INDEX IF NOT EXISTS idx_neighborhoods_geom_gist
ON neighborhoods USING GIST(geom);

-- Spatial index on neighborhood centroids
CREATE INDEX IF NOT EXISTS idx_neighborhoods_centroid_gist
ON neighborhoods USING GIST(centroid);

-- Regular indexes for relationships and lookups
CREATE INDEX IF NOT EXISTS idx_neighborhoods_district
ON neighborhoods(district_id);

CREATE INDEX IF NOT EXISTS idx_neighborhoods_code
ON neighborhoods(code);

-- =============================================
-- REGULAR INDEXES FOR OTHER TABLES
-- =============================================

-- Users
CREATE INDEX IF NOT EXISTS idx_users_email
ON users(email);

-- Refresh tokens
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id
ON refresh_tokens(user_id);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token
ON refresh_tokens(token);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at
ON refresh_tokens(expires_at);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_expires
ON refresh_tokens(user_id, expires_at);

-- Keywords
CREATE INDEX IF NOT EXISTS idx_keywords_user_id
ON keywords(user_id);

CREATE INDEX IF NOT EXISTS idx_keywords_keyword
ON keywords(keyword);

-- GEOINT scores
CREATE INDEX IF NOT EXISTS idx_geoint_keyword
ON geoint_scores(keyword_id);

CREATE INDEX IF NOT EXISTS idx_geoint_region
ON geoint_scores(region_type, region_id);

CREATE INDEX IF NOT EXISTS idx_geoint_score
ON geoint_scores(geoint_score);

CREATE UNIQUE INDEX IF NOT EXISTS idx_geoint_keyword_region
ON geoint_scores(keyword_id, region_type, region_id);

-- Competitors
CREATE INDEX IF NOT EXISTS idx_competitors_user_id
ON competitors(user_id);

CREATE INDEX IF NOT EXISTS idx_competitors_domain
ON competitors(domain);

-- Competitor snapshots
CREATE INDEX IF NOT EXISTS idx_competitor_snapshots_competitor_id
ON competitor_snapshots(competitor_id);

CREATE INDEX IF NOT EXISTS idx_competitor_snapshots_date
ON competitor_snapshots(snapshot_date);

-- Strategies
CREATE INDEX IF NOT EXISTS idx_strategies_user_id
ON strategies(user_id);

CREATE INDEX IF NOT EXISTS idx_strategies_status
ON strategies(status);

-- Strategy weeks
CREATE INDEX IF NOT EXISTS idx_strategy_weeks_strategy_id
ON strategy_weeks(strategy_id);

-- Strategy tasks
CREATE INDEX IF NOT EXISTS idx_strategy_tasks_week_id
ON strategy_tasks(week_id);

CREATE INDEX IF NOT EXISTS idx_strategy_tasks_status
ON strategy_tasks(status);

-- Media mentions
CREATE INDEX IF NOT EXISTS idx_media_mentions_user_id
ON media_mentions(user_id);

-- PR opportunities
CREATE INDEX IF NOT EXISTS idx_pr_opportunities_user_id
ON pr_opportunities(user_id);

-- Activities
CREATE INDEX IF NOT EXISTS idx_activities_user_id
ON activities(user_id);

CREATE INDEX IF NOT EXISTS idx_activities_created_at
ON activities(created_at);

-- =============================================
-- NOTES ON SPATIAL INDEXES
-- =============================================
--
-- GIST indexes enable fast spatial queries like:
--   - ST_Contains(geom, point)
--   - ST_Intersects(geom1, geom2)
--   - ST_DWithin(geom, point, distance)
--   - ST_Distance(geom1, geom2)
--
-- These are essential for GEOINT calculations that
-- find which regions contain specific coordinates.
-- =============================================
