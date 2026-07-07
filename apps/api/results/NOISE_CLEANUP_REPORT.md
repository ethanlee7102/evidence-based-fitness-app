# Corpus Noise-Chunk Cleanup — Report

**Date:** 2026-07-06 · **Phase:** 2 retrieval, final step (ROADMAP #10 / step 11′)

## Summary

Removed **1,387 bibliography / boilerplate chunks** from the corpus
(**8,284 → 6,897 chunks**, all 195 papers retained) and added a content-based
noise filter to the ingestion pipeline so future papers self-clean.

## Why

Reranking (shipped Phase 2) surfaced a failure mode vector search had hidden:
the cross-encoder **promotes reference-list chunks** because citation *titles*
are dense keyword matches for the query. In the shipped `sgnorm@0.15` config,
bibliography chunks landed at **rank 2–3 on CVD-001** and **rank 1 on OOS-002** —
zero-content chunks outranking real evidence. Across all 100 eval cases, **25 of
500 top-5 slots (5.0%) were noise**.

## Method

**Classify by chunk *text*, not section label.** Docling frequently fails to emit
a "References" header (esp. MDPI/Frontiers), so reference lists inherit the
preceding content section's label (`5. Conclusions`, `Glossary`); conversely a
chunk-boundary split can leave real prose under a `References` label (NUT-014).
The section label is unreliable in both directions, so it is only a secondary
vote — the text is the primary signal.

Rule (`src/core/noise_filter.py`):
- **biblio verdict** — author-initial + DOI + `[CrossRef]` density with a low
  prose-word ratio;
- **head-prose guard** — spare any chunk that *opens* with real prose (protects
  boundary chunks like NUT-014);
- **opening-front-matter guard** — spare MDPI/Frontiers first-page splices at
  `chunk_index ≤ 3` (title/abstract/intro chunks carrying `Citation:` /
  `Publisher's Note` metadata).

## Verification — 15 parallel agents

The classifier flagged **1,402 / 8,284 chunks (17.0%)**. Rather than delete
corpus data on a heuristic, **15 agents independently read every flagged chunk**
(94 each) and classified each as pure noise or a false positive.

- **Confirmed noise: 1,387** → deleted
- **False positives rescued: 15** (98.9% classifier precision) — every one the
  same pattern: a reference list fused with a trailing conclusion / dosage table
  / prescription (chunk-boundary spillage). Spared, not deleted.
- 0 hallucinated suspect IDs (all 15 validated against the flagged set).

## Deletion

Row-delete (**not re-ingest**) so survivor embeddings stay byte-identical → the
before/after retrieval comparison is a clean A/B. Full rows (incl. embeddings)
backed up first and verified (1,387/1,387, non-empty text + embedding present)
before any delete. `papers.total_chunks` reconciled for 194 papers.

- Decision record: `results/noise_review/final_verdict.json` (`keep_ids` / `delete_ids`)
- Reversible backup (local, gitignored): `results/noise_review/deleted_chunks_backup.json`

## Impact (measured offline, no eval run)

The full 2-hour eval was **deliberately skipped**: removing zero-content chunks
can't degrade answers (a freed top-5 slot is backfilled by real content or stays
equal), and the eval's small deltas would be dominated by Voyage embedding
non-determinism (~22% top-5 drift). Measured directly from the frozen fixtures
instead:

- **25 / 500 top-5 slots (5.0%)** across the 100 cases were noise chunks.
- **24 / 25** are provably backfilled by real content from the cached rank 6–20
  pool (the 25th needs a chunk from rank 21+, still real content).

## Ingestion filter (permanent, conservative)

`chunk_sections` now calls `is_noise(..., conservative=True)` — because ingestion
has no human reviewer, conservative mode spares any chunk with a ≥20-word prose
run **or** a dosage/statistic pattern. Validated to drop **0 of the 15 known
false positives** while still auto-removing ~39% of true noise. The error
direction is asymmetric-safe: it leaks recoverable noise, never silently drops
content. Covered by 13 offline unit tests (`tests/test_noise_filter.py`), CI-safe.
