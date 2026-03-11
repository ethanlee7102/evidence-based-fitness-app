-- Add columns to rag_traces for Phase 6 observability.
-- rewritten_query: the query after follow-up rewriting (NULL for first messages)
-- chunk_count: number of chunks retrieved (avoids parsing JSONB to count)
-- model: LLM model used for generation
-- grounded: whether the answer was backed by retrieved chunks

ALTER TABLE rag_traces ADD COLUMN rewritten_query TEXT;
ALTER TABLE rag_traces ADD COLUMN chunk_count INTEGER;
ALTER TABLE rag_traces ADD COLUMN model TEXT;
ALTER TABLE rag_traces ADD COLUMN grounded BOOLEAN;
