# Flame Fitness

[![CI](https://github.com/ethanlee7102/Gym-App-V2/actions/workflows/ci.yml/badge.svg)](https://github.com/ethanlee7102/Gym-App-V2/actions/workflows/ci.yml)

Flame Fitness is a full-stack workout app with an exercise-science research assistant built into it. The assistant answers training and nutrition questions from a library of 195 peer-reviewed papers and cites a source for every claim. Most of the engineering went into evaluation: building a way to measure whether the answers are actually correct, and then checking that the measurement itself could be trusted.

On the current corpus the system retrieves 79% of the facts a question expects (its weakest metric), scores 0.90 overall across five metrics, and refuses correctly on every out-of-scope question. To check that my eval was not just agreeing with itself, I ran it against Ragas, the industry-standard implementation. The two tools land within about one percent of each other on fact coverage.

## Highlights

- A real evaluation harness, not just a pipeline that runs. Five metrics computed from binary judgments (per-fact recall, per-claim faithfulness) over 100 test cases and 323 facts I checked by hand against the source papers.
- The eval is cross-validated. It runs against Ragas and against a second judge model (Claude), so the scores are not one model grading its own work.
- Retrieval changes were measured, not assumed. I tested a reranker that made results worse, worked out why, and replaced it with one that helped.
- It is honest about its limits. Recall is the weakest metric and this README says so, rather than leading with the numbers that look best.
- It is instrumented. Every query is traced with a latency breakdown across embedding, retrieval, and generation, the passages that were retrieved, and whether the answer came back grounded, so a bad answer can be debugged without rerunning it.
- Built to be safe to ship. All 195 papers are open-access under CC-BY, and every answer attributes its sources, so the corpus is safe to cite and use commercially.
- Every tool choice has a reason. What I built from scratch, what I reached for a framework for, and what I rejected are all listed below.

## Architecture

```
Ingestion (offline, per paper)
  PDF -> Docling + pymupdf extraction -> section-aware chunking
      -> Voyage embeddings (voyage-4-large, 1024d) -> Postgres + pgvector (HNSW)

Query (per question)
  question -> Voyage query embedding
           -> pgvector deep fetch (150 candidates)
           -> Voyage rerank-2.5
           -> score-gated per-paper cap -> top 5 passages
           -> Gemini 2.5 Flash -> cited answer, streamed over SSE

App
  React + TypeScript (Vite)  <->  FastAPI  <->  Supabase Postgres (row-level security)
```

The RAG assistant lives inside a working product. The app handles auth and onboarding, workout logging, and a 386-exercise library with 2,890 EMG-backed muscle-activation mappings, across 9 related tables and roughly 30 REST endpoints, all protected by row-level security so each user only sees their own data.

## Evaluation methodology

This is the part I spent the most time on, because measuring RAG quality is where most projects are weakest.

The judge started as a 1-to-5 Likert score and I migrated it to binary decomposition. A 1-to-5 rating has undefined gaps between adjacent points and judges cluster in the middle, so a single fuzzy number is unreliable. Instead each metric is now computed by arithmetic from many binary judgments: recall is the fraction of a question's expected facts that the retrieved passages support, faithfulness is the fraction of the answer's claims grounded in those passages. This is also how Ragas computes the same metrics under the hood, which makes the comparison between the two an honest apples-to-apples one.

Current baseline on 100 cases (98 answerable, 2 deliberately out of scope):

| Metric | Score | What it measures |
|---|---|---|
| Fact coverage (recall) | 0.79 | share of expected facts supported by the retrieved passages |
| Context relevancy | 0.88 | share of retrieved passages relevant to the question |
| Context precision | 0.96 | rank-weighted precision of the relevant passages |
| Faithfulness | 0.98 | share of answer claims grounded in the retrieved passages |
| Answer relevancy | pass (gate) | whether the answer addresses the question, used as a tripwire |
| Overall | 0.90 | mean of the scored metrics |

Recall is the weak spot and the one that carries real signal. The other metrics sit near the ceiling because the system genuinely does not hallucinate and stays on topic, so they discriminate less.

The eval is validated on two independent axes so it is not self-confirming. Both tools score the same frozen set of answers and retrieved passages, so any difference between them is the judge, not run-to-run variation in the pipeline.

- Against a different implementation (Ragas, same 100 cases): recall correlates at r = 0.75, and the mean scores are 0.791 for my judge versus 0.786 for Ragas.
- Against a different judge model (Claude Haiku 4.5): recall correlates at r = 0.56. Because recall judges the retrieved passages rather than the generator's text, a gap here is a difference in strictness between judges, not a model rewarding its own output.

Alongside the LLM judge there are deterministic checks that need no API calls: a citation validator that confirms every cited `[Author, Year]` maps to a passage that was actually retrieved (15 ungrounded of 1,669, all in one case), a refusal check, and a verbatim-copy check.

## Retrieval, measured

The retriever is a deep fetch followed by reranking and a per-paper cap, and each step earned its place against the eval.

I first tried a local reranker (FlashRank, an MS-MARCO model). It made retrieval worse on both judges. The reranked top 5 had lower average similarity and pulled 41% of its passages from beyond the vector top 20, because a 2021 web-search model mis-ranks dense scientific prose. I had built the reranker behind a swappable interface, so moving to Voyage rerank-2.5 was one class and a config change, and it beat plain vector search on recall.

A single paper often dominated the top 5, which reads as a thin answer even when the retrieval is correct. A hard cap fixed that but hurt questions where one paper genuinely is the answer, so I built a score-gated cap that only diversifies when the alternative passage is nearly as good. It cut single-paper answers from 64% to 38% of cases with no drop in answer quality.

Reranking then surfaced a problem vector search had hidden: it promoted reference-list entries, because a citation title is a dense keyword match for the query. I wrote a content-based classifier (the section label is unreliable because the extractor mislabels reference lists), had every flagged passage reviewed before deletion, and removed 1,387 of them, leaving all 195 papers intact.

## Tools considered and rejected

The guiding rule: use a framework where it solves a problem I would otherwise have to solve, build it myself where a framework would hide the system without saving real work.

| Decision | Choice | Reason |
|---|---|---|
| v1 retrieve-and-generate | Custom | The flow is about 50 lines of direct HTTP calls. A framework would add a layer, not remove one. |
| Evaluation judge | Custom | Writing the metric prompts is the only way to actually understand what they measure. |
| Ingestion pipeline | Custom | Academic-paper header detection via bounding-box matching. No off-the-shelf tool handles PMC papers well. |
| Trace storage | Custom | Tied to this system's latency split and grounded flag, which generic tools do not capture. |
| Chunking | langchain-text-splitters | Recursive splitting is a solved problem. |
| Eval cross-validation | Ragas | The canonical reference implementation, which is the point of using it as a check. |
| Embeddings and reranking | Voyage | Best measured fit for scientific text; 1024 dims fit pgvector natively. |
| v2 orchestration | LangGraph | A router with conditional retries is a state machine, where the abstraction is worth it. |
| Vector store | pgvector | One database for auth, data, and vectors at this scale. A dedicated vector DB adds ops for no gain. |
| Local reranker | Rejected (FlashRank) | Measured: it degraded ranking on scientific prose. |
| Eval framework wrapper | Rejected (DeepEval) | Its Ragas module is a reimplementation, which would weaken the cross-validation claim. |
| Dedicated vector DB | Rejected (Pinecone, Weaviate) | Unneeded at roughly 7,000 chunks. |

## Tech stack

Frontend is React, TypeScript, Vite, and Tailwind. Backend is Python and FastAPI. Data, auth, and vector search all run on Supabase Postgres with pgvector and row-level security. Embeddings are Voyage `voyage-4-large`, reranking is Voyage `rerank-2.5`, and generation is Gemini 2.5 Flash. Continuous integration runs on GitHub Actions (linting plus the offline test suite) on every pull request.

## What is not solved yet

- Recall is the weakest metric at 79%. Some questions need passages that sit beyond the fetch depth, which reranking cannot recover on its own.
- The judge is validated against other judges and a second model, not yet against human labels. A human-alignment study (Cohen's kappa against a hand-labeled sample) is the next eval step.
- Hybrid retrieval (BM25 plus vector) was measured on this corpus and did not help, because the failure mode is one paper dominating rather than vocabulary mismatch, so it is deferred.

Planned next is v2, an agentic version built on a LangGraph router that sends a question to a literature branch, a workout-data branch over the user's own logged sets, or an exercise-info branch, with a judge node that can trigger a bounded retry. That work is in progress. A LangSmith UI is also planned on top of the existing trace table, for per-case drill-down alongside the durable storage rather than in place of it.

## Running locally

Prerequisites: Node 18+, pnpm 9+, Python 3.11+, and a Supabase project.

```bash
# install dependencies
pnpm install

# backend environment
cd apps/api
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Apply the migrations in `supabase/migrations/` in order against your Supabase project. Then set environment variables:

```bash
# apps/api/.env
SUPABASE_URL=...
SUPABASE_SECRET_KEY=...
VOYAGE_API_KEY=...            # embeddings and reranking
GOOGLE_API_KEY=...            # Gemini generation

# apps/web/.env
VITE_SUPABASE_URL=...
VITE_SUPABASE_PUBLISHABLE_KEY=...
VITE_API_URL=http://localhost:8000
```

```bash
# from the repo root, runs frontend and backend together
pnpm dev
```

Loading the paper corpus is a separate step. The ingestion scripts live in `apps/api/scripts/` (`ingest_paper.py` for a single PDF, `ingest_batch.py` for a manifest). The evaluation harness runs from `apps/api/scripts/evaluate_rag.py`.
