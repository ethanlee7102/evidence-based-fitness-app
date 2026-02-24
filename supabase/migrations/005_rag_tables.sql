-- RAG Chatbot Tables
-- Enables pgvector, creates papers/chunks for research corpus,
-- chat_sessions/chat_messages for conversation persistence,
-- rag_traces for observability, and match_chunks RPC for retrieval.

-- =============================================================================
-- 1. Enable pgvector extension
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- 2. Papers table — one row per research paper
-- =============================================================================
CREATE TABLE papers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    authors TEXT NOT NULL,
    year INTEGER NOT NULL,
    journal TEXT,
    doi TEXT,
    url TEXT,
    category TEXT NOT NULL CHECK (category IN (
        'hypertrophy', 'strength', 'nutrition', 'endurance',
        'recovery', 'mobility', 'programming', 'general'
    )),
    study_type TEXT CHECK (study_type IN (
        'meta-analysis', 'systematic-review', 'rct', 'review',
        'observational', 'case-study', 'other'
    )),
    abstract TEXT,
    content_hash TEXT UNIQUE NOT NULL,  -- SHA-256 for dedup
    total_chunks INTEGER NOT NULL DEFAULT 0,
    embedding_model TEXT NOT NULL,      -- e.g. 'voyage-4-large'
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 3. Chunks table — one row per text chunk from a paper
-- =============================================================================
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    section TEXT,                        -- e.g. 'Results', 'Discussion'
    page_start INTEGER,                  -- first page this chunk appears on
    page_end INTEGER,                    -- last page (if chunk spans pages)
    token_count INTEGER,                 -- for prompt assembly budget
    embedding VECTOR(1024) NOT NULL,    -- voyage-4-large dimensions
    chunking_method TEXT NOT NULL DEFAULT 'section-aware',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(paper_id, chunk_index)
);

-- HNSW index for fast cosine similarity search
CREATE INDEX chunks_embedding_idx ON chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- =============================================================================
-- 4. Chat sessions + messages
-- =============================================================================
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX chat_sessions_user_id_idx ON chat_sessions(user_id);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX chat_messages_session_id_idx ON chat_messages(session_id);

-- =============================================================================
-- 5. RAG traces — observability for every RAG query
-- =============================================================================
CREATE TABLE rag_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    message_id UUID REFERENCES chat_messages(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    retrieved_chunks JSONB DEFAULT '[]'::jsonb,
    prompt_sent TEXT,
    llm_response TEXT,
    embedding_time_ms INTEGER,
    retrieval_time_ms INTEGER,
    generation_time_ms INTEGER,
    total_time_ms INTEGER,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX rag_traces_user_id_idx ON rag_traces(user_id);
CREATE INDEX rag_traces_session_id_idx ON rag_traces(session_id);

-- =============================================================================
-- 6. RLS policies
-- =============================================================================
ALTER TABLE papers ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag_traces ENABLE ROW LEVEL SECURITY;

-- Papers and chunks: public read (everyone can search research)
CREATE POLICY "Papers are readable by all authenticated users"
    ON papers FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Chunks are readable by all authenticated users"
    ON chunks FOR SELECT
    TO authenticated
    USING (true);

-- Chat sessions: users own their sessions
CREATE POLICY "Users can read their own sessions"
    ON chat_sessions FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own sessions"
    ON chat_sessions FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own sessions"
    ON chat_sessions FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own sessions"
    ON chat_sessions FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- Chat messages: users own messages through session ownership
CREATE POLICY "Users can read messages in their sessions"
    ON chat_messages FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM chat_sessions
            WHERE chat_sessions.id = chat_messages.session_id
            AND chat_sessions.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert messages in their sessions"
    ON chat_messages FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM chat_sessions
            WHERE chat_sessions.id = chat_messages.session_id
            AND chat_sessions.user_id = auth.uid()
        )
    );

-- RAG traces: users own their traces
CREATE POLICY "Users can read their own traces"
    ON rag_traces FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own traces"
    ON rag_traces FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- =============================================================================
-- 7. match_chunks RPC — vector similarity search with paper metadata
-- =============================================================================
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding VECTOR(1024),
    match_count INTEGER DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.3,
    filter_category TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    paper_id UUID,
    chunk_text TEXT,
    section TEXT,
    chunk_index INTEGER,
    page_start INTEGER,
    page_end INTEGER,
    similarity FLOAT,
    title TEXT,
    authors TEXT,
    year INTEGER,
    journal TEXT,
    doi TEXT,
    url TEXT,
    category TEXT,
    study_type TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id AS chunk_id,
        c.paper_id,
        c.text AS chunk_text,
        c.section,
        c.chunk_index,
        c.page_start,
        c.page_end,
        1 - (c.embedding <=> query_embedding) AS similarity,
        p.title,
        p.authors,
        p.year,
        p.journal,
        p.doi,
        p.url,
        p.category,
        p.study_type
    FROM chunks c
    JOIN papers p ON c.paper_id = p.id
    WHERE
        (filter_category IS NULL OR p.category = filter_category)
        AND 1 - (c.embedding <=> query_embedding) > similarity_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
