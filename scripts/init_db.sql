-- Medusa RAG — Database Initialization
-- Run automatically on first Postgres container start

CREATE TABLE IF NOT EXISTS query_traces (
    id              SERIAL PRIMARY KEY,
    trace_id        VARCHAR(36)  UNIQUE NOT NULL,
    request_id      VARCHAR(36)  NOT NULL,
    query           TEXT         NOT NULL,
    prompt_version  VARCHAR(32)  NOT NULL,
    fallback_level  VARCHAR(32),
    answer          TEXT,
    retrieval_scores JSONB       DEFAULT '[]',
    token_usage     JSONB        DEFAULT '{}',
    spans           JSONB        DEFAULT '[]',
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_traces_request_id  ON query_traces (request_id);
CREATE INDEX IF NOT EXISTS idx_query_traces_created_at  ON query_traces (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_traces_prompt_ver  ON query_traces (prompt_version);
CREATE INDEX IF NOT EXISTS idx_query_traces_fallback    ON query_traces (fallback_level) WHERE fallback_level IS NOT NULL;

CREATE TABLE IF NOT EXISTS documents (
    id           SERIAL PRIMARY KEY,
    doc_id       VARCHAR(36)  UNIQUE NOT NULL,
    filename     VARCHAR(512) NOT NULL,
    chunk_count  INTEGER      NOT NULL,
    source_hash  VARCHAR(64)  NOT NULL,
    metadata     JSONB        DEFAULT '{}',
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_source_hash ON documents (source_hash);
