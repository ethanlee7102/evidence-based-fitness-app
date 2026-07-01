"""Offline unit tests for the reranker (src/core/reranker.py).

Exercise the pure/deterministic logic with NO flashrank, NO ONNX, NO network:
  - apply_per_paper_cap (greedy diversity cap, suppression reporting, edge cases),
  - rerank() wrapper behavior with a STUBBED scoring model (sort, score attach,
    similarity preservation, top_n truncation, empty input).

Intentionally NOT marked `eval` — must run in CI under `pytest -m "not eval"`, which
runs without flashrank installed. The lazy `import flashrank` (inside the backend ctor)
is never triggered here.
"""

import asyncio

from src.core.reranker import apply_per_paper_cap, apply_score_gated_cap, rerank
from src.schema.rag import ChunkResponse


def _chunk(
    chunk_id: str,
    paper_id: str,
    text: str = "text",
    similarity: float = 0.5,
    rerank_score: float | None = None,
) -> ChunkResponse:
    return ChunkResponse(
        chunk_id=chunk_id,
        paper_id=paper_id,
        chunk_text=text,
        chunk_index=0,
        similarity=similarity,
        rerank_score=rerank_score,
        title="Title",
        authors="Author A",
        year=2020,
        category="hypertrophy",
    )


# --- apply_per_paper_cap -----------------------------------------------------


def test_cap_breaks_single_paper_monopoly():
    # 5 chunks all from paper P, cap=2 → only 2 survive even though top_n=5.
    chunks = [_chunk(f"c{i}", "P") for i in range(5)]
    kept = apply_per_paper_cap(chunks, cap=2, top_n=5)
    assert len(kept) == 2
    assert [c.chunk_id for c in kept] == ["c0", "c1"]


def test_cap_keeps_distinct_papers_and_preserves_order():
    chunks = [_chunk(f"c{i}", f"P{i}") for i in range(5)]
    kept = apply_per_paper_cap(chunks, cap=2, top_n=5)
    assert [c.chunk_id for c in kept] == ["c0", "c1", "c2", "c3", "c4"]


def test_cap_does_not_relax_when_too_few_papers():
    # Only 2 papers, cap=2, top_n=5 → max fillable is 4; cap is NOT relaxed to backfill.
    chunks = [
        _chunk("a0", "A"), _chunk("a1", "A"), _chunk("a2", "A"),
        _chunk("b0", "B"), _chunk("b1", "B"), _chunk("b2", "B"),
    ]
    kept = apply_per_paper_cap(chunks, cap=2, top_n=5)
    assert len(kept) == 4
    assert [c.chunk_id for c in kept] == ["a0", "a1", "b0", "b1"]


def test_cap_returns_all_when_fewer_than_top_n():
    chunks = [_chunk("c0", "A"), _chunk("c1", "B"), _chunk("c2", "C")]
    kept = apply_per_paper_cap(chunks, cap=2, top_n=5)
    assert [c.chunk_id for c in kept] == ["c0", "c1", "c2"]


def test_cap_reports_suppressed_chunks():
    # P's 3rd+ chunks rank high but get chopped — the "is cap too aggressive?" signal.
    chunks = [_chunk(f"c{i}", "P") for i in range(4)] + [_chunk("q0", "Q")]
    kept, suppressed = apply_per_paper_cap(chunks, cap=2, top_n=5, return_suppressed=True)
    assert [c.chunk_id for c in kept] == ["c0", "c1", "q0"]
    assert [c.chunk_id for c in suppressed] == ["c2", "c3"]


def test_cap_empty_input():
    assert apply_per_paper_cap([], cap=2, top_n=5) == []


def test_cap_zero_means_no_cap():
    # cap<=0 disables the limit (shipped default): one paper can fill all top_n slots.
    chunks = [_chunk(f"c{i}", "P") for i in range(8)]
    kept = apply_per_paper_cap(chunks, cap=0, top_n=5)
    assert [c.chunk_id for c in kept] == ["c0", "c1", "c2", "c3", "c4"]


# --- apply_score_gated_cap ---------------------------------------------------


def test_score_gate_keeps_over_cap_chunk_when_clearly_better():
    # P's 3rd chunk (0.97) far outscores the only alternative (Q, 0.50) -> keep it.
    chunks = [
        _chunk("p0", "P", rerank_score=0.99),
        _chunk("p1", "P", rerank_score=0.98),
        _chunk("p2", "P", rerank_score=0.97),
        _chunk("q0", "Q", rerank_score=0.50),
    ]
    kept = apply_score_gated_cap(chunks, cap=2, margin=0.05, top_n=3)
    assert [c.chunk_id for c in kept] == ["p0", "p1", "p2"]  # cap exceeded — relevance wins


def test_score_gate_diversifies_when_alternative_is_close():
    # P's 3rd chunk (0.97) barely beats Q (0.96) -> diversify (suppress p2, take q0).
    chunks = [
        _chunk("p0", "P", rerank_score=0.99),
        _chunk("p1", "P", rerank_score=0.98),
        _chunk("p2", "P", rerank_score=0.97),
        _chunk("q0", "Q", rerank_score=0.96),
    ]
    kept, suppressed = apply_score_gated_cap(
        chunks, cap=2, margin=0.05, top_n=3, return_suppressed=True
    )
    assert [c.chunk_id for c in kept] == ["p0", "p1", "q0"]
    assert [c.chunk_id for c in suppressed] == ["p2"]


def test_score_gate_normalize_uses_fraction_of_range():
    # Range over the pool = 0.99 - 0.59 = 0.40. P's 3rd chunk (0.97) beats Q (0.95) by
    # 0.02 = 5% of range. frac 0.10 -> diversify; frac 0.03 -> keep.
    chunks = [
        _chunk("p0", "P", rerank_score=0.99),
        _chunk("p1", "P", rerank_score=0.98),
        _chunk("p2", "P", rerank_score=0.97),
        _chunk("q0", "Q", rerank_score=0.95),
        _chunk("r0", "R", rerank_score=0.59),  # widens the range
    ]
    div = apply_score_gated_cap(chunks, cap=2, margin=0.10, top_n=3, normalize=True)
    assert [c.chunk_id for c in div] == ["p0", "p1", "q0"]  # 5% < 10% -> diversify
    keep = apply_score_gated_cap(chunks, cap=2, margin=0.03, top_n=3, normalize=True)
    assert [c.chunk_id for c in keep] == ["p0", "p1", "p2"]  # 5% > 3% -> keep


def test_score_gate_large_margin_behaves_like_hard_cap():
    chunks = [_chunk(f"p{i}", "P", rerank_score=0.9 - i * 0.01) for i in range(4)] + [
        _chunk("q0", "Q", rerank_score=0.5)
    ]
    kept = apply_score_gated_cap(chunks, cap=2, margin=10.0, top_n=5)
    assert [c.chunk_id for c in kept] == ["p0", "p1", "q0"]  # only 2 of P, like a hard cap


# --- rerank() wrapper with a stubbed model -----------------------------------


class _StubReranker:
    """Scores each passage by a fixed text→score map (aligned to input order).

    Implements both score (sync/local path) and ascore (async/API path) so the rerank()
    wrapper tests are agnostic to which provider is the configured default.
    """

    def __init__(self, scores_by_text: dict[str, float]):
        self._scores = scores_by_text

    def score(self, query: str, passages: list[str]) -> list[float]:
        return [self._scores[p] for p in passages]

    async def ascore(self, query: str, passages: list[str]) -> list[float]:
        return self.score(query, passages)


def _run(coro):
    return asyncio.run(coro)


def test_rerank_sorts_by_score_and_attaches_without_touching_similarity(monkeypatch):
    import src.core.reranker as rr

    chunks = [
        _chunk("low", "A", text="low", similarity=0.9),    # high vector sim...
        _chunk("high", "B", text="high", similarity=0.1),  # ...but low; rerank flips it
        _chunk("mid", "C", text="mid", similarity=0.5),
    ]
    stub = _StubReranker({"low": 0.1, "high": 0.9, "mid": 0.5})
    monkeypatch.setattr(rr, "_get_reranker", lambda: stub)

    out = _run(rerank("q", chunks))

    assert [c.chunk_id for c in out] == ["high", "mid", "low"]  # sorted by rerank score
    assert [c.rerank_score for c in out] == [0.9, 0.5, 0.1]
    # similarity preserved (NOT overwritten by rerank score)
    assert {c.chunk_id: c.similarity for c in out} == {"low": 0.9, "high": 0.1, "mid": 0.5}


def test_rerank_top_n_truncates(monkeypatch):
    import src.core.reranker as rr

    chunks = [_chunk(f"c{i}", f"P{i}", text=f"c{i}") for i in range(5)]
    stub = _StubReranker({f"c{i}": float(i) for i in range(5)})
    monkeypatch.setattr(rr, "_get_reranker", lambda: stub)

    out = _run(rerank("q", chunks, top_n=2))
    assert [c.chunk_id for c in out] == ["c4", "c3"]


def test_rerank_empty_input_returns_empty(monkeypatch):
    import src.core.reranker as rr

    monkeypatch.setattr(rr, "_get_reranker", lambda: _StubReranker({}))
    assert _run(rerank("q", [])) == []


def test_rerank_does_not_mutate_input_chunks(monkeypatch):
    import src.core.reranker as rr

    chunks = [_chunk("c0", "A", text="c0")]
    monkeypatch.setattr(rr, "_get_reranker", lambda: _StubReranker({"c0": 0.7}))

    _run(rerank("q", chunks))
    assert chunks[0].rerank_score is None  # original untouched (model_copy used)


# --- retrieve_reranked orchestrator (stubbed fetch + reranker) ---------------


def test_retrieve_reranked_orchestration(monkeypatch):
    """Deep fetch (no floor, fetch_depth) -> rerank -> per-paper cap -> top_n."""
    import src.core.reranker as rr
    import src.core.retrieval as rv
    from src.schema.rag import RetrievalResult

    # A saturated pool: 4 chunks from paper P, 2 from Q, 1 from R.
    pool = (
        [_chunk(f"p{i}", "P", text=f"p{i}") for i in range(4)]
        + [_chunk(f"q{i}", "Q", text=f"q{i}") for i in range(2)]
        + [_chunk("r0", "R", text="r0")]
    )

    captured = {}

    async def fake_retrieve_chunks(**kwargs):
        captured.update(kwargs)
        return RetrievalResult(chunks=pool, query=kwargs["query"], retrieval_time_ms=12.0, embedding_time_ms=3.0)

    # Stub reranker: score by reverse insertion order so p0 ranks highest, r0 lowest.
    scores = {c.chunk_text: float(len(pool) - i) for i, c in enumerate(pool)}
    monkeypatch.setattr(rv, "retrieve_chunks", fake_retrieve_chunks)
    monkeypatch.setattr(rr, "_get_reranker", lambda: _StubReranker(scores))

    # cap_margin=0 pins the HARD-cap path this test asserts (else it uses the shipped
    # score-gated default and P's high-scoring 3rd chunk would be kept).
    out = _run(rv.retrieve_reranked(
        "q", top_n=5, fetch_depth=150, ef_search=500, per_paper_cap=2, cap_margin=0.0
    ))

    # Deep fetch requested the pool depth (not top_n) with the floor disabled.
    assert captured["top_k"] == 150
    assert captured["ef_search"] == 500
    assert captured["similarity_threshold"] == -1.0
    # Hard cap=2 breaks P's monopoly: keep p0,p1 then q0,q1 then r0 — p2,p3 chopped.
    assert [c.chunk_id for c in out.chunks] == ["p0", "p1", "q0", "q1", "r0"]
    # Timing threaded through.
    assert out.embedding_time_ms == 3.0
    assert out.rerank_time_ms >= 0.0
