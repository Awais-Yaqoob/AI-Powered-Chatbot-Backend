-- ============================================================
-- WP AI Chatbot SaaS - Supabase Schema
-- ============================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- SITES TABLE - One row per registered WordPress site
-- ============================================================
CREATE TABLE sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_url TEXT NOT NULL UNIQUE,
    site_name TEXT,
    api_key TEXT NOT NULL UNIQUE DEFAULT gen_random_uuid()::text,
    site_type TEXT DEFAULT 'general', -- general | medical | legal | financial
    plan TEXT DEFAULT 'starter',      -- starter | agency | premium
    llm_model TEXT DEFAULT 'gpt-4o-mini', -- gpt-4o-mini | claude-haiku
    enable_global_fallback BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    indexed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CHUNKS TABLE - Stores embedded content per site
-- ============================================================
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- text-embedding-3-small dimension
    token_count INT,
    chunk_index INT,
    post_type TEXT DEFAULT 'page', -- page | post | faq | custom
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast similarity search per site
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Index for filtering by site
CREATE INDEX idx_chunks_site_id ON chunks(site_id);

-- ============================================================
-- GLOBAL KNOWLEDGE BASE - Fallback for all sites
-- ============================================================
CREATE TABLE global_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT,
    content TEXT NOT NULL,
    category TEXT,  -- e.g., 'general', 'medical-disclaimer', 'legal-notice'
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON global_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- ============================================================
-- CONVERSATIONS TABLE - Analytics & history
-- ============================================================
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    matched_chunks UUID[] DEFAULT '{}',
    used_global_fallback BOOLEAN DEFAULT FALSE,
    had_disclaimer BOOLEAN DEFAULT FALSE,
    tokens_used INT DEFAULT 0,
    response_time_ms INT,
    flagged_keyword TEXT,  -- if crisis keyword detected
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_site_id ON conversations(site_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);

-- ============================================================
-- INDEXING JOBS TABLE - Track scrape/index status
-- ============================================================
CREATE TABLE indexing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending', -- pending | running | completed | failed
    pages_found INT DEFAULT 0,
    pages_indexed INT DEFAULT 0,
    chunks_created INT DEFAULT 0,
    error_message TEXT,
    triggered_by TEXT DEFAULT 'manual', -- manual | save_post | schedule
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ANALYTICS VIEW - Popular queries per site
-- ============================================================
CREATE VIEW site_analytics AS
SELECT
    site_id,
    COUNT(*) AS total_conversations,
    COUNT(DISTINCT session_id) AS unique_sessions,
    AVG(tokens_used) AS avg_tokens,
    AVG(response_time_ms) AS avg_response_ms,
    COUNT(*) FILTER (WHERE used_global_fallback) AS global_fallback_count,
    COUNT(*) FILTER (WHERE flagged_keyword IS NOT NULL) AS crisis_flags,
    DATE_TRUNC('day', created_at) AS day
FROM conversations
GROUP BY site_id, DATE_TRUNC('day', created_at);

-- ============================================================
-- FUNCTION: Semantic search per site
-- ============================================================
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding VECTOR(1536),
    match_site_id UUID,
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    url TEXT,
    title TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.content,
        c.url,
        c.title,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks c
    WHERE c.site_id = match_site_id
      AND 1 - (c.embedding <=> query_embedding) > similarity_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================
-- FUNCTION: Global fallback search
-- ============================================================
CREATE OR REPLACE FUNCTION match_global_chunks(
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 3,
    similarity_threshold FLOAT DEFAULT 0.75
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    title TEXT,
    category TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        g.id,
        g.content,
        g.title,
        g.category,
        1 - (g.embedding <=> query_embedding) AS similarity
    FROM global_chunks g
    WHERE 1 - (g.embedding <=> query_embedding) > similarity_threshold
    ORDER BY g.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
