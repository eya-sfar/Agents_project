-- =============================================================
-- University Observatory — PostgreSQL Schema
-- database/migrations/init_schema.sql
-- =============================================================
-- language: sql

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- fuzzy text search

-- =============================================================
-- LABS
-- =============================================================
CREATE TABLE IF NOT EXISTS labs (
    lab_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    department      VARCHAR(255),
    university      VARCHAR(255),
    country         VARCHAR(100),
    website         TEXT,
    description     TEXT,
    num_researchers INTEGER DEFAULT 0,
    active_projects INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- RESEARCHERS
-- =============================================================
CREATE TABLE IF NOT EXISTS researchers (
    researcher_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    email           VARCHAR(255),
    lab_id          UUID REFERENCES labs(lab_id) ON DELETE SET NULL,
    department      VARCHAR(255),
    position        VARCHAR(100),                   -- Professor, PhD, PostDoc …
    h_index         INTEGER DEFAULT 0,
    total_citations INTEGER DEFAULT 0,
    publications    INTEGER DEFAULT 0,
    google_scholar_id VARCHAR(50),
    dblp_pid        VARCHAR(100),
    orcid           VARCHAR(50),
    profile_url     TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- PUBLICATIONS
-- =============================================================
CREATE TABLE IF NOT EXISTS publications (
    publication_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           TEXT NOT NULL,
    abstract        TEXT,
    year            INTEGER,
    citations       INTEGER DEFAULT 0,
    venue           VARCHAR(255),                   -- journal / conference
    doi             VARCHAR(200),
    url             TEXT,
    pub_type        VARCHAR(50),                    -- journal, conference, thesis …
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Publication <-> Researcher (many-to-many)
CREATE TABLE IF NOT EXISTS publication_authors (
    publication_id  UUID REFERENCES publications(publication_id) ON DELETE CASCADE,
    researcher_id   UUID REFERENCES researchers(researcher_id) ON DELETE CASCADE,
    author_order    INTEGER DEFAULT 1,
    PRIMARY KEY (publication_id, researcher_id)
);

-- =============================================================
-- EXPERTISE
-- =============================================================
CREATE TABLE IF NOT EXISTS expertise (
    expertise_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    researcher_id   UUID NOT NULL REFERENCES researchers(researcher_id) ON DELETE CASCADE,
    area            VARCHAR(255) NOT NULL,
    keywords        TEXT[],                         -- array of keywords
    score           FLOAT DEFAULT 1.0,              -- relevance weight
    source          VARCHAR(50) DEFAULT 'manual',   -- manual | inferred | scraped
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- CLUSTERS
-- =============================================================
CREATE TABLE IF NOT EXISTS clusters (
    cluster_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255),
    description     TEXT,
    algorithm       VARCHAR(50) DEFAULT 'kmeans',
    run_date        TIMESTAMPTZ DEFAULT NOW(),
    parameters      JSONB                           -- e.g. {"n_clusters": 8}
);

CREATE TABLE IF NOT EXISTS cluster_members (
    cluster_id      UUID REFERENCES clusters(cluster_id) ON DELETE CASCADE,
    researcher_id   UUID REFERENCES researchers(researcher_id) ON DELETE CASCADE,
    distance        FLOAT DEFAULT 0.0,              -- distance from centroid
    PRIMARY KEY (cluster_id, researcher_id)
);

-- =============================================================
-- COLLABORATION RECOMMENDATIONS
-- =============================================================
CREATE TABLE IF NOT EXISTS collaborations (
    collab_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    researcher_a_id UUID NOT NULL REFERENCES researchers(researcher_id) ON DELETE CASCADE,
    researcher_b_id UUID NOT NULL REFERENCES researchers(researcher_id) ON DELETE CASCADE,
    score           FLOAT NOT NULL,                 -- 0-1 compatibility score
    reason          TEXT,                           -- short explanation
    status          VARCHAR(50) DEFAULT 'suggested', -- suggested | accepted | rejected
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (researcher_a_id, researcher_b_id)
);

-- =============================================================
-- AGENT RUNS (audit log)
-- =============================================================
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name      VARCHAR(100) NOT NULL,
    status          VARCHAR(50) DEFAULT 'started',  -- started | completed | failed
    records_processed INTEGER DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    finished_at     TIMESTAMPTZ
);

-- =============================================================
-- INDEXES
-- =============================================================
CREATE INDEX IF NOT EXISTS idx_researchers_lab ON researchers(lab_id);
CREATE INDEX IF NOT EXISTS idx_researchers_name ON researchers USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_publications_year ON publications(year);
CREATE INDEX IF NOT EXISTS idx_publications_title ON publications USING gin(title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_expertise_researcher ON expertise(researcher_id);
CREATE INDEX IF NOT EXISTS idx_expertise_area ON expertise(area);
CREATE INDEX IF NOT EXISTS idx_collab_a ON collaborations(researcher_a_id);
CREATE INDEX IF NOT EXISTS idx_collab_b ON collaborations(researcher_b_id);

-- =============================================================
-- UPDATED_AT trigger
-- =============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_researchers_updated
    BEFORE UPDATE ON researchers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_labs_updated
    BEFORE UPDATE ON labs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();