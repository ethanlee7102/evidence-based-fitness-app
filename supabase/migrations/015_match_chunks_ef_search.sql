-- Add an optional ef_search parameter to match_chunks.
--
-- Why: pgvector's HNSW index has a query-time accuracy/speed knob, hnsw.ef_search
-- (the search "beam width"), whose default is 40. The rule of thumb is
-- ef_search >= the number of rows requested. Our production path requests
-- LIMIT 5 (5 << 40, fine), but Phase 2 deep-candidate fetches for reranking
-- (e.g. top-150) with ef_search stuck at 40 return an APPROXIMATE set that can
-- silently skip genuinely-near chunks ranked 41+. This parameter lets a caller
-- widen the beam for deep fetches.
--
-- ef_search defaults to NULL = leave the session/database default untouched,
-- so the existing LIMIT-5 production behavior is exactly preserved.
--
-- DROP required: adding a parameter changes the function signature, and a
-- RETURNS TABLE function can't be CREATE OR REPLACE'd into a new shape.

DROP FUNCTION IF EXISTS match_chunks(VECTOR(1024), INTEGER, FLOAT, TEXT);

CREATE FUNCTION match_chunks(
    query_embedding VECTOR(1024),
    match_count INTEGER DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.3,
    filter_category TEXT DEFAULT NULL,
    ef_search INTEGER DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    paper_id UUID,
    chunk_text TEXT,
    section TEXT,
    chunk_index INTEGER,
    page_start INTEGER,
    page_end INTEGER,
    token_count INTEGER,
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
    -- Widen the HNSW search beam for this transaction when requested. Must run
    -- before the index scan below; set_config(..., is_local => true) scopes it
    -- to this transaction so it never leaks to other queries on the pooled conn.
    -- (SET can't take a dynamic value, hence set_config.)
    IF ef_search IS NOT NULL THEN
        PERFORM set_config('hnsw.ef_search', ef_search::text, true);
    END IF;

    RETURN QUERY
    SELECT
        c.id AS chunk_id,
        c.paper_id,
        c.text AS chunk_text,
        c.section,
        c.chunk_index,
        c.page_start,
        c.page_end,
        c.token_count,
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
