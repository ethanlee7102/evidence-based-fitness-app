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
_BACKOFF_DELAYS = [1, 2, 4]


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
        if not passages:
            return []
        if not config.VOYAGE_API_KEY:
            raise ValueError("VOYAGE_API_KEY not configured")

        for attempt in range(len(_BACKOFF_DELAYS) + 1):
            resp = await _get_async_client().post(
                _VOYAGE_RERANK_URL,
                headers={
                    "Authorization": f"Bearer {config.VOYAGE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"query": query, "documents": passages, "model": self._model},
            )
            if resp.status_code == 200:
                break
            if resp.status_code in _RETRYABLE_STATUSES and attempt < len(_BACKOFF_DELAYS):
                delay = _BACKOFF_DELAYS[attempt]
                logger.warning(
                    f"Voyage rerank {resp.status_code}, retry {attempt + 1} in {delay}s..."
                )
                await asyncio.sleep(delay)
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
