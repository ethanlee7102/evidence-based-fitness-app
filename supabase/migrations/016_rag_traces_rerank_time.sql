-- Phase 2 step 9' observability: record cross-encoder rerank latency per trace.
-- Nullable, default 0 so existing rows and the rerank-disabled path are unaffected.
-- total_time_ms is computed in the app layer (retrieval + rerank + generation), not here.

ALTER TABLE rag_traces ADD COLUMN rerank_time_ms INTEGER DEFAULT 0;
