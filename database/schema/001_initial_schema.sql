-- =============================================
-- STRATYON Database Schema - Initial Setup
-- =============================================
-- Version: 1.0
-- Created: 2026-01-06
-- Liquibase-ready format
--
-- Prerequisites:
--   - PostgreSQL 13+
--   - PostGIS extension
-- =============================================

-- Enable PostGIS extension for geospatial support
CREATE EXTENSION IF NOT EXISTS postgis;

-- =============================================
-- USERS & AUTHENTICATION
-- =============================================

-- Subscription plan enum
DO $$ BEGIN
    CREATE TYPE subscriptionplan AS ENUM (
        'free',
        'insight',
        'strategy',
        'growth',
        'enterprise'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,

    -- Profile
    full_name VARCHAR(255),
    company_name VARCHAR(255),
    phone VARCHAR(20),

    -- Subscription
    plan subscriptionplan NOT NULL DEFAULT 'free',
    plan_started_at TIMESTAMP,
    plan_expires_at TIMESTAMP,

    -- Limits based on plan
    max_keywords INTEGER DEFAULT 3,
    max_competitors INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    is_superuser BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- Refresh tokens table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    token VARCHAR(512) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    device_info VARCHAR(255),
    ip_address VARCHAR(45)
);

-- =============================================
-- GEOGRAPHIC INTELLIGENCE
-- =============================================

-- Region type enum
DO $$ BEGIN
    CREATE TYPE regiontype AS ENUM ('PROVINCE', 'DISTRICT', 'NEIGHBORHOOD');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Provinces (İller) - 81 provinces
CREATE TABLE IF NOT EXISTS provinces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(2) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    region VARCHAR(50),
    population INTEGER,
    area_km2 FLOAT,

    -- Geospatial columns (SRID 4326 = WGS84)
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL,
    centroid GEOMETRY(POINT, 4326),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Districts (İlçeler) - ~970 districts
CREATE TABLE IF NOT EXISTS districts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    province_id UUID NOT NULL,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    population INTEGER,
    area_km2 FLOAT,

    -- Geospatial columns
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL,
    centroid GEOMETRY(POINT, 4326),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Neighborhoods (Mahalleler) - ~50,000 neighborhoods
CREATE TABLE IF NOT EXISTS neighborhoods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    district_id UUID NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    neighborhood_type VARCHAR(20),

    -- Geospatial columns
    geom GEOMETRY(MULTIPOLYGON, 4326),
    centroid GEOMETRY(POINT, 4326),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- KEYWORD TRACKING
-- =============================================

-- Keywords table
CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,

    -- Keyword data
    keyword VARCHAR(255) NOT NULL,
    root_form VARCHAR(255),
    intent VARCHAR(50),

    -- Search data
    avg_monthly_searches INTEGER DEFAULT 0,
    search_trend VARCHAR(10),
    cpc_avg INTEGER,

    -- Settings
    is_active BOOLEAN DEFAULT true,
    refresh_frequency VARCHAR(20) DEFAULT 'daily',

    -- Metadata
    nlp_metadata JSONB,
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_refreshed_at TIMESTAMP
);

-- GEOINT scores table
CREATE TABLE IF NOT EXISTS geoint_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword_id UUID NOT NULL,

    -- Region reference (polymorphic)
    region_type regiontype NOT NULL,
    region_id UUID NOT NULL,

    -- Score components (0-100)
    search_index FLOAT DEFAULT 0,
    trend_score FLOAT DEFAULT 0,
    demographic_fit FLOAT DEFAULT 0,
    competition_gap FLOAT DEFAULT 0,

    -- Composite score (0-100)
    geoint_score FLOAT NOT NULL,

    -- Trend metadata
    trend_direction VARCHAR(10),
    trend_change_pct FLOAT,

    -- Raw data for debugging/analysis
    raw_data JSONB,

    -- Timestamps
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- COMPETITOR INTELLIGENCE
-- =============================================

-- Competitors table
CREATE TABLE IF NOT EXISTS competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,

    -- Competitor info
    domain VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    category VARCHAR(100),

    -- Current metrics
    domain_authority INTEGER,
    page_authority INTEGER,
    trust_flow INTEGER,
    citation_flow INTEGER,

    -- Traffic estimates
    organic_traffic INTEGER,
    organic_keywords INTEGER,
    paid_keywords INTEGER,

    -- Backlinks
    total_backlinks INTEGER,
    referring_domains INTEGER,

    -- Additional metadata
    technologies JSONB,
    social_media JSONB,
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_analyzed_at TIMESTAMP
);

-- Competitor snapshots table
CREATE TABLE IF NOT EXISTS competitor_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id UUID NOT NULL,

    -- Snapshot metrics
    domain_authority INTEGER,
    organic_traffic INTEGER,
    organic_keywords INTEGER,
    total_backlinks INTEGER,
    referring_domains INTEGER,

    -- Top ranking keywords (sample)
    top_keywords JSONB,

    -- Timestamp
    snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- =============================================
-- STRATEGY PLANNING
-- =============================================

-- Strategy status enum
DO $$ BEGIN
    CREATE TYPE strategystatus AS ENUM (
        'DRAFT',
        'ACTIVE',
        'PAUSED',
        'COMPLETED',
        'ARCHIVED'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Strategies table
CREATE TABLE IF NOT EXISTS strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,

    -- Strategy metadata
    name VARCHAR(255) NOT NULL,
    primary_goal TEXT NOT NULL,
    target_keywords TEXT[],
    target_regions TEXT[],

    -- Timeline
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    status strategystatus NOT NULL DEFAULT 'DRAFT',

    -- Budget
    total_budget FLOAT,
    budget_spent FLOAT DEFAULT 0,

    -- AI-generated content
    executive_summary TEXT,
    opportunities JSONB,
    threats JSONB,
    kpi_targets JSONB,

    -- Performance tracking
    current_kpis JSONB,
    completion_percentage INTEGER DEFAULT 0,

    -- LLM metadata
    generated_by_model VARCHAR(50),
    generation_timestamp TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Strategy weeks table
CREATE TABLE IF NOT EXISTS strategy_weeks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL,

    week_number INTEGER NOT NULL,
    week_start_date TIMESTAMP NOT NULL,
    week_end_date TIMESTAMP NOT NULL,

    -- Week objectives
    focus_area VARCHAR(255),
    objectives JSONB,
    budget_allocated FLOAT,

    -- Progress
    completion_percentage INTEGER DEFAULT 0,
    notes TEXT
);

-- Task status and priority enums
DO $$ BEGIN
    CREATE TYPE taskstatus AS ENUM (
        'TODO',
        'IN_PROGRESS',
        'COMPLETED',
        'BLOCKED',
        'CANCELLED'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE taskpriority AS ENUM (
        'LOW',
        'MEDIUM',
        'HIGH',
        'URGENT'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Strategy tasks table
CREATE TABLE IF NOT EXISTS strategy_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_id UUID NOT NULL,

    -- Task details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),

    -- Metadata
    status taskstatus NOT NULL DEFAULT 'TODO',
    priority taskpriority NOT NULL DEFAULT 'MEDIUM',

    -- Effort estimate
    estimated_hours FLOAT,
    actual_hours FLOAT,
    estimated_cost FLOAT,

    -- Assignment
    assigned_to VARCHAR(255),
    due_date TIMESTAMP,
    completed_at TIMESTAMP
);

-- =============================================
-- MEDIA MONITORING
-- =============================================

-- Media mentions table
CREATE TABLE IF NOT EXISTS media_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,

    -- Mention details
    brand_query VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    url VARCHAR(1000) NOT NULL UNIQUE,
    publication VARCHAR(255),
    author VARCHAR(255),

    -- Content
    excerpt TEXT,
    full_text TEXT,

    -- Sentiment analysis
    sentiment VARCHAR(20),
    sentiment_score FLOAT,

    -- Metrics
    estimated_reach INTEGER,
    social_shares INTEGER,

    -- Timestamps
    published_at TIMESTAMP,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PR opportunities table
CREATE TABLE IF NOT EXISTS pr_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,

    -- Opportunity details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    publication VARCHAR(255),

    -- Relevance
    relevance_score FLOAT,
    category VARCHAR(100),

    -- Contact info
    journalist_name VARCHAR(255),
    journalist_email VARCHAR(255),
    journalist_twitter VARCHAR(100),

    -- Status
    contacted BOOLEAN DEFAULT false,
    contacted_at TIMESTAMP,
    response_received BOOLEAN DEFAULT false,
    outcome VARCHAR(50),

    -- Timestamps
    identified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- =============================================
-- ACTIVITY TRACKING
-- =============================================

-- Activity type enum
DO $$ BEGIN
    CREATE TYPE activitytype AS ENUM (
        'keyword_added',
        'keyword_deleted',
        'strategy_created',
        'strategy_updated',
        'competitor_added',
        'competitor_analyzed',
        'geoint_calculated',
        'alert_triggered'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Activities table
CREATE TABLE IF NOT EXISTS activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,

    -- Activity details
    activity_type activitytype NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,

    -- Optional reference to related entity
    entity_type VARCHAR(50),
    entity_id UUID,

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- END OF SCHEMA
-- =============================================
