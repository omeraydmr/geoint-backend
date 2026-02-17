-- =============================================
-- STRATYON Database Schema - Competitor Enhancements
-- =============================================
-- Version: 1.1
-- Created: 2026-01-27
-- Description: Adds advanced competitor analysis features
-- =============================================

-- =============================================
-- COMPETITORS TABLE ENHANCEMENTS
-- =============================================

-- Add new columns to competitors table
ALTER TABLE competitors
ADD COLUMN IF NOT EXISTS estimated_ad_spend INTEGER,
ADD COLUMN IF NOT EXISTS estimated_ad_keywords INTEGER,
ADD COLUMN IF NOT EXISTS content_score INTEGER,
ADD COLUMN IF NOT EXISTS social_followers JSONB,
ADD COLUMN IF NOT EXISTS ai_insights JSONB;

-- Add comments for documentation
COMMENT ON COLUMN competitors.estimated_ad_spend IS 'Estimated monthly advertising spend in USD';
COMMENT ON COLUMN competitors.estimated_ad_keywords IS 'Number of keywords with paid ads';
COMMENT ON COLUMN competitors.content_score IS 'Content quality score 0-100';
COMMENT ON COLUMN competitors.social_followers IS 'Social media followers: {twitter, linkedin, facebook, instagram}';
COMMENT ON COLUMN competitors.ai_insights IS 'Cached AI-generated SWOT analysis and recommendations';

-- =============================================
-- COMPETITOR BACKLINKS TABLE
-- =============================================

-- Create competitor_backlinks table for detailed backlink tracking
CREATE TABLE IF NOT EXISTS competitor_backlinks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,

    -- Backlink details
    source_url VARCHAR(2048) NOT NULL,
    source_domain VARCHAR(255) NOT NULL,
    target_url VARCHAR(2048),
    anchor_text VARCHAR(500),

    -- Authority metrics
    domain_authority INTEGER,
    page_authority INTEGER,

    -- Link attributes
    link_type VARCHAR(20) DEFAULT 'dofollow',
    is_image INTEGER DEFAULT 0,

    -- Timestamps
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_competitor_backlinks_competitor_id
    ON competitor_backlinks(competitor_id);
CREATE INDEX IF NOT EXISTS idx_competitor_backlinks_source_domain
    ON competitor_backlinks(source_domain);
CREATE INDEX IF NOT EXISTS idx_competitor_backlinks_first_seen
    ON competitor_backlinks(first_seen);

-- Add comment
COMMENT ON TABLE competitor_backlinks IS 'Detailed backlink profile for tracked competitors';

-- =============================================
-- END OF MIGRATION
-- =============================================
