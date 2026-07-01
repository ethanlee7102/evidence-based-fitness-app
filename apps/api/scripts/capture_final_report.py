"""Airtight 3-way capstone capture: vector-only vs rerank-no-cap vs rerank-sgnorm@0.15.

Controls the sole noise source (the Voyage embedding is non-deterministic; HNSW + the
Voyage reranker are deterministic) by embedding each query ONCE and feeding that same
vector to all three retrievals. So the three configs differ only by their genuine
retrieval logic — no run-to-run retrieval noise. Generates an answer per config from the
shared embeddings, then both judges score each (full 5 metrics).

Emits 3 fixtures in the standard format:
    results/final_vector.json   — bi-encoder top-5 (production original)
    results/final_nocap.json    — deep fetch -> Voyage rerank -> top-5
    results/final_sgnorm.json   — deep fetch -> Voyage rerank -> score-gated cap -> top-5

Usage:  python -m scripts.capture_final_report
Then judge each:  evaluate_rag --from-fixture results/final_<cfg>.json --combined
                  evaluate_rag_ragas --fixture results/final_<cfg>.json
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

from scripts.evaluate_rag import load_dataset
from src.core.embedding_provider import embed_query
from src.core.llm_provider import generate
from src.core.rag_pipeline import (
    _RAG_MAX_TOKENS,
    _RAG_TEMPERATURE,
    SYSTEM_PROMPT,
    build_rag_prompt,
)
from src.core.reranker import apply_per_paper_cap, apply_score_gated_cap, rerank
from src.db import get_supabase
from src.schema.rag import ChunkResponse
from src.utils.config import config

DATASET = Path(__file__).resolve().parent.parent / "tests" / "eval" / "test_dataset.json"
INTER_CASE_DELAY = 2.0


def _match(emb, k, threshold, ef_search=None):
    params = {
        "query_embedding": emb, "match_count": k,
        "similarity_threshold": threshold, "filter_category": None,
    }
    if ef_search is not None:
        params["ef_search"] = ef_search
    rows = get_supabase().rpc("match_chunks", params).execute().data
    return [ChunkResponse(**r) for r in rows]


async def _answer(question, chunks):
    prompt = build_rag_prompt(question, chunks)
    return await generate(
        prompt=prompt, system=SYSTEM_PROMPT,
        temperature=_RAG_TEMPERATURE, max_tokens=_RAG_MAX_TOKENS,
    )


def _entry(case, chunks, answer):
    return {
        "id": case["id"], "question": case["question"], "category": case.get("category"),
        "expected_facts": case.get("expected_facts", []),
        "difficulty": case.get("difficulty", "unknown"), "tags": case.get("tags", []),
        "answer": answer, "grounded": len(chunks) > 0, "rewritten_query": None,
        "model": config.LLM_MODEL, "retrieval_time_ms": 0.0, "generation_time_ms": 0.0,
        "chunks": [c.model_dump(mode="json") for c in chunks],
    }


async def main():
    ap = argparse.ArgumentParser(description="Airtight 3-way capstone capture")
    ap.add_argument("--ids", nargs="+")
    args = ap.parse_args()
    dataset = load_dataset(str(DATASET), args.ids)

    out = {"vector": [], "nocap": [], "sgnorm": []}
    start = time.time()
    fails = []
    for i, case in enumerate(dataset):
        q = case["question"]
        try:
            emb = await embed_query(q)  # ONCE — shared by all three configs
            v = _match(emb, config.RAG_TOP_K, config.RAG_SIMILARITY_THRESHOLD)
            pool = _match(emb, config.RERANK_FETCH_DEPTH, -1.0, ef_search=config.RERANK_EF_SEARCH)
            reranked = await rerank(q, pool)
            nc = apply_per_paper_cap(reranked, cap=0, top_n=config.RERANK_TOP_N)
            sg = apply_score_gated_cap(reranked, cap=2, margin=0.15, top_n=config.RERANK_TOP_N, normalize=True)
            out["vector"].append(_entry(case, v, await _answer(q, v)))
            out["nocap"].append(_entry(case, nc, await _answer(q, nc)))
            out["sgnorm"].append(_entry(case, sg, await _answer(q, sg)))
            print(f"  [{i+1}/{len(dataset)}] {case['id']}: v={len(v)} nc={len(nc)} sg={len(sg)}")
        except Exception as e:  # noqa: BLE001
            print(f"  [{case['id']}] FAILED: {e}")
            fails.append(case["id"])
        if i < len(dataset) - 1:
            await asyncio.sleep(INTER_CASE_DELAY)

    for cfg, cases in out.items():
        fixture = {
            "metadata": {
                "config": cfg, "model": config.LLM_MODEL, "shared_embedding": True,
                "total_cases": len(dataset), "captured_cases": len(cases),
                "failed_cases": len(fails), "failed_ids": fails,
                "duration_s": round(time.time() - start, 1),
            },
            "cases": cases,
        }
        path = f"results/final_{cfg}.json"
        Path(path).write_text(json.dumps(fixture, indent=2, default=str))
        print(f"wrote {path} ({len(cases)} cases)")


if __name__ == "__main__":
    asyncio.run(main())
