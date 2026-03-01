-- Add token_count to match_chunks RPC return type.
-- DROP required because PostgreSQL cannot CREATE OR REPLACE when the
-- RETURNS TABLE columns change (adding token_count changes the row type).

DROP FUNCTION IF EXISTS match_chunks(VECTOR(1024), INTEGER, FLOAT, TEXT);

CREATE FUNCTION match_chunks(
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
