"""Cross-encoder reranking (Phase 2, step 9').

Stage 2 of a retrieve-then-rerank pipeline: a bi-encoder (Voyage embeddings) cheaply
narrows the corpus to a deep candidate pool, then a cross-encoder rescores that pool by
reading each (query, chunk) pair jointly — far more accurate than the bi-encoder's
separately-encoded cosine similarity, at a cost that's only tractable on a small pool.

Design notes:
  - The reranker MODEL is swappable behind `Reranker` + `_build_reranker()` dispatch
    (mirrors the LLM_PROVIDER convention). FlashRank is the initial local/CPU baseline;
    an API reranker (e.g. Voyage rerank) is a later config change, not a rewrite.
  - FlashRank is a LOCAL ONNX library, not a network provider — so it does NOT use the
    shared-httpx-client pattern, only the swappable-interface spirit.
  - `import flashrank` is LAZY (inside the backend ctor) so this module — and the pure
    `apply_per_paper_cap` — import fine in CI/offline without flashrank installed.
  - ONNX inference is synchronous and CPU-bound; `rerank()` runs it via
    `asyncio.to_thread` so it never blocks the FastAPI event loop. `_rerank_sync` is
    private precisely so nothing calls the blocking path on the loop by accident.
"""

import asyncio
import logging
from collections import Counter
from typing import Protocol

import httpx

from src.schema.rag import ChunkResponse
from src.utils.config import config

logger = logging.getLogger(__name__)

_VOYAGE_RERANK_URL = "https://api.voyageai.com/v1/rerank"
# Providers whose scoring is async-native (network) rather than sync/CPU-local.
_ASYNC_PROVIDERS = {"voyage"}
_RETRYABLE_STATUSES = {429, 500, 502, 503, 529}

# Adaptive pacing for the rerank API. The pace PERSISTS across calls (module-level), so
# sustained rate-limiting doesn't make every call re-probe from 1s — once throttled, the
# next call pre-waits the elevated pace. AIMD-style: double on a 429, decay on success.
_MAX_ATTEMPTS = 5
_PACE_BASE = 1.0     # first backoff step
_PACE_MAX = 30.0     # ceiling
_PACE_DECAY = 0.6    # multiply pace by this on each success (gentle recovery)
_pace = 0.0          # current inter-call delay, seconds


def _retry_after_seconds(response: httpx.Response) -> float:
    """Honor a Retry-After header (seconds form) when present; else 0."""
    raw = response.headers.get("retry-after")
    if not raw:
        return 0.0
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.0


class Reranker(Protocol):
    """A reranker scores how relevant each passage is to the query.

    Returns one score per passage, aligned to the input order (higher = more relevant).
    Sorting/selection is the caller's job — this contract is just the scoring model.

    Local/CPU backends (FlashRank) implement sync `score`; API backends (Voyage)
    implement async `ascore`. `rerank()` dispatches on config.RERANK_PROVIDER.
    """

    def score(self, query: str, passages: list[str]) -> list[float]: ...


class _FlashRankReranker:
    """Local cross-encoder via FlashRank (ONNX, CPU). Lazy model load on first use."""

    def __init__(self, model: str, max_length: int, cache_dir: str | None) -> None:
        # Lazy import: only pulled in when reranking is actually enabled, so CI/offline
        # paths that merely import this module never need flashrank installed.
        try:
            from flashrank import Ranker, RerankRequest
        except ImportError as e:  # pragma: no cover - exercised only without the dep
            raise RuntimeError(
                "flashrank is not installed but reranking is enabled. "
                "Add it to requirements (`pip install flashrank`) or set "
                "RERANK_ENABLED=false."
            ) from e

        self._RerankRequest = RerankRequest
        # First construction downloads the model (~34MB for MiniLM-L-12-v2) to cache_dir.
        self._ranker = Ranker(
            model_name=model,
            max_length=max_length,
            **({"cache_dir": cache_dir} if cache_dir else {}),
        )
        logger.info(f"Loaded reranker model '{model}' (max_length={max_length})")

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        # id = input index, so we can map FlashRank's score-sorted output back to order.
        request = self._RerankRequest(
            query=query,
            passages=[{"id": i, "text": text} for i, text in enumerate(passages)],
        )
        results = self._ranker.rerank(request)
        scores = [0.0] * len(passages)
        for r in results:
            scores[int(r["id"])] = float(r["score"])
        return scores


# Shared async client for API rerankers (Voyage). Lazy; closed in app.py lifespan.
_async_client: httpx.AsyncClient | None = None


def _get_async_client() -> httpx.AsyncClient:
    global _async_client
    if _async_client is None:
        _async_client = httpx.AsyncClient(timeout=60.0)
    return _async_client


async def aclose() -> None:
    """Close the shared async client (call from the app lifespan hook)."""
    global _async_client
    if _async_client is not None:
        await _async_client.aclose()
        _async_client = None


class _VoyageReranker:
    """Voyage rerank API (rerank-2.5 / rerank-2.5-lite). Async/network, not local.

    150 chunks of ~800 tokens + a short query is ~123K tokens, well under the
    600K-token per-call ceiling, so the whole pool reranks in one request.
    """

    def __init__(self, model: str) -> None:
        self._model = model

    async def ascore(self, query: str, passages: list[str]) -> list[float]:
        global _pace
        if not passages:
            return []
        if not config.VOYAGE_API_KEY:
            raise ValueError("VOYAGE_API_KEY not configured")

        resp = None
        for attempt in range(_MAX_ATTEMPTS):
            # Carry throttle state across calls AND attempts: a recently-throttled run
            # pre-waits the elevated pace instead of restarting at 1s every call.
            if _pace > 0:
                await asyncio.sleep(_pace)
            resp = await _get_async_client().post(
                _VOYAGE_RERANK_URL,
                headers={
                    "Authorization": f"Bearer {config.VOYAGE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"query": query, "documents": passages, "model": self._model},
            )
            if resp.status_code == 200:
                _pace *= _PACE_DECAY  # ease off as throttling clears
                if _pace < 0.1:
                    _pace = 0.0
                break
            if resp.status_code in _RETRYABLE_STATUSES and attempt < _MAX_ATTEMPTS - 1:
                # Ratchet the persistent pace up (double, honor Retry-After, cap).
                _pace = min(
                    _PACE_MAX,
                    max(_retry_after_seconds(resp), max(_pace, _PACE_BASE) * 2),
                )
                logger.warning(
                    f"Voyage rerank {resp.status_code}; pace -> {_pace:.1f}s "
                    f"(attempt {attempt + 1}/{_MAX_ATTEMPTS})"
                )
                continue
            raise RuntimeError(f"Voyage rerank API error {resp.status_code}: {resp.text}")

        data = resp.json()
        # Reference API returns "data"; older docs show "results" — accept either.
        items = data.get("data") or data.get("results") or []
        scores = [0.0] * len(passages)
        for it in items:
            scores[int(it["index"])] = float(it["relevance_score"])
        return scores


def _build_reranker() -> Reranker:
    """Construct the configured reranker backend. Dispatch on RERANK_PROVIDER."""
    provider = config.RERANK_PROVIDER.lower()
    if provider == "flashrank":
        return _FlashRankReranker(
            model=config.RERANK_MODEL,
            max_length=config.RERANK_MAX_LENGTH,
            cache_dir=config.RERANK_CACHE_DIR or None,
        )
    if provider == "voyage":
        return _VoyageReranker(model=config.RERANK_MODEL)
    raise ValueError(f"Unknown RERANK_PROVIDER: {config.RERANK_PROVIDER!r}")


_reranker: Reranker | None = None


def _get_reranker() -> Reranker:
    """Lazy singleton — loads the model once, reuses it (cf. _get_converter in ingestion)."""
    global _reranker
    if _reranker is None:
        _reranker = _build_reranker()
    return _reranker


def _attach_and_sort(
    chunks: list[ChunkResponse], scores: list[float]
) -> list[ChunkResponse]:
    """Attach rerank_score to each chunk and return a NEW list sorted desc by it.
    model_copy avoids mutating the caller's objects; `similarity` is left untouched."""
    scored = [
        chunk.model_copy(update={"rerank_score": s})
        for chunk, s in zip(chunks, scores, strict=True)
    ]
    scored.sort(key=lambda c: c.rerank_score, reverse=True)
    return scored


def _score_blocking(query: str, passages: list[str]) -> list[float]:
    """Sync scoring for local backends. PRIVATE — call only via asyncio.to_thread so the
    CPU-bound ONNX inference (and first-use model load) never blocks the event loop."""
    return _get_reranker().score(query, passages)


async def rerank(
    query: str, chunks: list[ChunkResponse], top_n: int | None = None
) -> list[ChunkResponse]:
    """Rescore `chunks` against `query`, sorted desc by relevance.

    Dispatches on the backend: API rerankers (Voyage) are awaited directly; local
    CPU rerankers (FlashRank) run off the event loop via asyncio.to_thread. `top_n=None`
    returns the whole pool scored+sorted (the caller applies the per-paper cap).
    """
    if not chunks:
        return []
    passages = [c.chunk_text for c in chunks]
    if config.RERANK_PROVIDER.lower() in _ASYNC_PROVIDERS:
        scores = await _get_reranker().ascore(query, passages)
    else:
        scores = await asyncio.to_thread(_score_blocking, query, passages)
    scored = _attach_and_sort(chunks, scores)
    return scored[:top_n] if top_n is not None else scored


def apply_per_paper_cap(
    chunks: list[ChunkResponse],
    cap: int,
    top_n: int,
    return_suppressed: bool = False,
):
    """Keep at most `cap` chunks per paper, walking in the given order, until `top_n`
    filled. Pure function — no I/O, no model.

    Cross-encoders score each chunk pointwise and do NOT break single-paper saturation
    on their own, so this cap is a first-class stage (applied AFTER reranking, on
    accurate scores). Input is assumed already sorted by desired priority (rerank score);
    output preserves that order.

    Edge cases:
      - Fewer distinct papers than needed: returns < top_n (the cap is NOT relaxed to
        backfill — that would defeat diversity). Caller/measurement can see the shortfall.
      - Total chunks < top_n: returns all (capped).

    With return_suppressed=True, returns (kept, suppressed) where `suppressed` are chunks
    that ranked high enough to make top_n but were dropped by the cap — the signal for
    whether cap is chopping a legitimately-concentrated paper's correct chunk.

    cap <= 0 means "no per-paper limit" (the shipped default — the ablation found the
    cap harmful); chunks are then taken in order up to top_n.
    """
    # cap <= 0 disables the limit (more than any single paper could contribute).
    effective_cap = cap if cap > 0 else len(chunks) + 1
    kept: list[ChunkResponse] = []
    suppressed: list[ChunkResponse] = []
    per_paper: Counter[str] = Counter()

    for chunk in chunks:
        if len(kept) >= top_n:
            break
        if per_paper[chunk.paper_id] >= effective_cap:
            suppressed.append(chunk)
            continue
        per_paper[chunk.paper_id] += 1
        kept.append(chunk)

    if return_suppressed:
        return kept, suppressed
    return kept


def apply_score_gated_cap(
    chunks: list[ChunkResponse],
    cap: int,
    margin: float,
    top_n: int,
    normalize: bool = False,
    return_suppressed: bool = False,
):
    """Per-paper cap a paper may EXCEED when doing so costs little relevance.

    Walking rerank-sorted chunks: a chunk whose paper is already at `cap` is kept anyway
    if it outscores the best still-available *new-paper* chunk by more than `margin` (the
    dominant paper's chunk is clearly better — keep it); otherwise it's suppressed so a
    new paper can take the slot (the alternative is nearly as good — diversify for free).

    `margin` tunes the spectrum: ~0 behaves like no cap, large behaves like a hard cap.
    It's a within-query relative comparison, so it doesn't depend on absolute score
    calibration. Requires chunks pre-sorted desc by rerank_score.

    normalize=True interprets `margin` as a FRACTION of the query's score range (computed
    over the top candidates) rather than a raw score gap — the calibration-robust form,
    since reranker score spreads vary widely across queries. Recommended: rerankers like
    Voyage compress the top scores, so a fixed absolute margin behaves inconsistently.
    """
    denom = 1.0
    if normalize and chunks:
        # Range over the top candidates that actually compete for the top_n slots, so the
        # fraction means the same thing regardless of how compressed a query's scores are.
        window = [c.rerank_score or 0.0 for c in chunks[: max(20, 4 * top_n)]]
        denom = (max(window) - min(window)) or 1e-9

    kept: list[ChunkResponse] = []
    suppressed: list[ChunkResponse] = []
    per_paper: Counter[str] = Counter()
    n = len(chunks)

    for i, c in enumerate(chunks):
        if len(kept) >= top_n:
            break
        if per_paper[c.paper_id] < cap:
            per_paper[c.paper_id] += 1
            kept.append(c)
            continue
        # c's paper is at the cap. The best under-cap alternative still ahead of us is the
        # first such chunk (chunks are score-sorted) — what diversity would admit instead.
        alt = next(
            (chunks[j] for j in range(i + 1, n) if per_paper[chunks[j].paper_id] < cap),
            None,
        )
        score = c.rerank_score or 0.0
        if alt is None or (score - (alt.rerank_score or 0.0)) / denom > margin:
            per_paper[c.paper_id] += 1
            kept.append(c)  # exceed cap: clearly better, or nothing to diversify to
        else:
            suppressed.append(c)  # diversify: the alternative is nearly as good

    if return_suppressed:
        return kept, suppressed
    return kept
