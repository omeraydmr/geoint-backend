-- Migration: Competitor comparison history table
-- Stores historical competitor SERP comparison snapshots

CREATE TABLE IF NOT EXISTS competitor_comparison_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    keyword_id UUID NOT NULL,
    user_domain VARCHAR(255),
    competitor_domains JSONB NOT NULL,
    region_type VARCHAR(10) DEFAULT 'il',
    results JSONB NOT NULL,
    summary JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_comp_history_user
ON competitor_comparison_history(user_id);

CREATE INDEX IF NOT EXISTS idx_comp_history_keyword
ON competitor_comparison_history(keyword_id);

CREATE INDEX IF NOT EXISTS idx_comp_history_created
ON competitor_comparison_history(created_at DESC);

-- Foreign keys
DO $$ BEGIN
    ALTER TABLE competitor_comparison_history
    ADD CONSTRAINT fk_comp_history_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE competitor_comparison_history
    ADD CONSTRAINT fk_comp_history_keyword_id
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
