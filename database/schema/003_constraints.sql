-- =============================================
-- STRATYON Database - Foreign Key Constraints
-- =============================================
-- Version: 1.0
-- Created: 2026-01-06
--
-- Foreign key constraints ensure referential
-- integrity across related tables.
-- All constraints are idempotent (safe to re-run).
-- =============================================

-- =============================================
-- USERS & AUTHENTICATION CONSTRAINTS
-- =============================================

-- Refresh tokens -> Users
DO $$ BEGIN
    ALTER TABLE refresh_tokens
    ADD CONSTRAINT fk_refresh_tokens_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =============================================
-- GEOGRAPHIC CONSTRAINTS
-- =============================================

-- Districts -> Provinces
DO $$ BEGIN
    ALTER TABLE districts
    ADD CONSTRAINT fk_districts_province_id
    FOREIGN KEY (province_id) REFERENCES provinces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Neighborhoods -> Districts
DO $$ BEGIN
    ALTER TABLE neighborhoods
    ADD CONSTRAINT fk_neighborhoods_district_id
    FOREIGN KEY (district_id) REFERENCES districts(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =============================================
-- KEYWORD & GEOINT CONSTRAINTS
-- =============================================

-- Keywords -> Users
DO $$ BEGIN
    ALTER TABLE keywords
    ADD CONSTRAINT fk_keywords_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- GEOINT scores -> Keywords
DO $$ BEGIN
    ALTER TABLE geoint_scores
    ADD CONSTRAINT fk_geoint_scores_keyword_id
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =============================================
-- COMPETITOR CONSTRAINTS
-- =============================================

-- Competitors -> Users
DO $$ BEGIN
    ALTER TABLE competitors
    ADD CONSTRAINT fk_competitors_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Competitor snapshots -> Competitors
DO $$ BEGIN
    ALTER TABLE competitor_snapshots
    ADD CONSTRAINT fk_competitor_snapshots_competitor_id
    FOREIGN KEY (competitor_id) REFERENCES competitors(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =============================================
-- STRATEGY CONSTRAINTS
-- =============================================

-- Strategies -> Users
DO $$ BEGIN
    ALTER TABLE strategies
    ADD CONSTRAINT fk_strategies_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Strategy weeks -> Strategies
DO $$ BEGIN
    ALTER TABLE strategy_weeks
    ADD CONSTRAINT fk_strategy_weeks_strategy_id
    FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Strategy tasks -> Strategy weeks
DO $$ BEGIN
    ALTER TABLE strategy_tasks
    ADD CONSTRAINT fk_strategy_tasks_week_id
    FOREIGN KEY (week_id) REFERENCES strategy_weeks(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =============================================
-- MEDIA MONITORING CONSTRAINTS
-- =============================================

-- Media mentions -> Users
DO $$ BEGIN
    ALTER TABLE media_mentions
    ADD CONSTRAINT fk_media_mentions_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- PR opportunities -> Users
DO $$ BEGIN
    ALTER TABLE pr_opportunities
    ADD CONSTRAINT fk_pr_opportunities_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =============================================
-- ACTIVITY CONSTRAINTS
-- =============================================

-- Activities -> Users
DO $$ BEGIN
    ALTER TABLE activities
    ADD CONSTRAINT fk_activities_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =============================================
-- ADDITIONAL CONSTRAINTS
-- =============================================

-- Ensure unique token for refresh tokens
DO $$ BEGIN
    ALTER TABLE refresh_tokens
    ADD CONSTRAINT uq_refresh_tokens_token UNIQUE (token);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =============================================
-- CONSTRAINT NAMING CONVENTION
-- =============================================
--
-- fk_{table}_{column}      = Foreign key constraint
-- uq_{table}_{column}      = Unique constraint
-- pk_{table}              = Primary key constraint
-- chk_{table}_{condition} = Check constraint
--
-- =============================================
