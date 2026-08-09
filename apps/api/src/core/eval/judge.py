"""Shared transport layer for the LLM-as-judge.

This module holds the provider-agnostic plumbing every judge call needs, factored
out from the metric logic (which now lives in `binary_judge.py`):

- `_generate_with_retry` — generate with transport retry (429 + any 5xx) and the
  `claude-*` / Gemini provider dispatch.
- `_generate_and_parse` — regenerate-on-parse-failure loop at escalating
  temperatures (Gemini at temp 0 tends to reproduce an identical malformed reply).
- `_extract_json_block` / `_format_chunks_for_judge` — response + prompt helpers.
- `JudgeParseError` — the signal that drives a regenerate; after retries exhaust
  it propagates so the caller can turn it into an ERRORED metric (never a
  synthesized fallback value).

Historical note: this file previously also contained the holistic 1-5 Likert judge
(five emitted-rating metrics + combined mode). That was replaced by the
binary/decomposed judge (`binary_judge.py`, ROADMAP #25) — metrics are now
proportions computed from binary atoms, not emitted ratings. Git history preserves
the old judge; the 1-5 result files in `results/` remain valid as frozen history.
"""

import asyncio
import logging
import re

from src.core import anthropic_provider, llm_provider
from src.utils.config import config

logger = logging.getLogger(__name__)


def _is_retryable_error(err: str) -> bool:
    """True if a provider RuntimeError string carries a retryable HTTP status.

    Both providers raise `RuntimeError("... API error <code>: <body>")`. Retry
    on 429 (rate limit) and any 5xx — notably Anthropic's 529 (overloaded),
    which the old `"503" in err` check silently missed.
    """
    match = re.search(r"API error (\d{3})", err)
    if not match:
        return False
    code = int(match.group(1))
    return code == 429 or code >= 500


class JudgeParseError(ValueError):
    """Raised when a judge response cannot be parsed into a valid result.

    Distinct from transport errors (429/5xx). Triggers a regenerate-and-retry in
    `_generate_and_parse`; after the retries exhaust it propagates so the caller
    can turn it into an ERRORED metric (score=None) — never a synthesized value.
    """


JUDGE_SYSTEM = """\
You are an expert evaluator for a Retrieval-Augmented Generation (RAG) system \
that answers exercise science questions using research papers. \
Score strictly according to the rubric. Return ONLY valid JSON.\
"""


def _format_chunks_for_judge(chunks: list) -> str:
    """Format chunks with metadata and full text for judge prompts.

    Numbered `[Chunk 1] .. [Chunk N]` in retrieval order, so the prompt index a
    judge references equals the chunk's retrieval rank (relied on by the per-chunk
    relevancy/precision verdicts in `binary_judge.py`).
    """
    if not chunks:
        return "(No chunks retrieved)"

    parts = []
    for i, chunk in enumerate(chunks, 1):
        # Support both ChunkResponse objects and dicts
        if hasattr(chunk, "authors"):
            authors = chunk.authors
            year = chunk.year
            section = chunk.section or "N/A"
            similarity = chunk.similarity
            text = chunk.chunk_text
        else:
            authors = chunk.get("authors", "Unknown")
            year = chunk.get("year", "?")
            section = chunk.get("section", "N/A")
            similarity = chunk.get("similarity", 0.0)
            text = chunk.get("chunk_text", "")

        parts.append(
            f"[Chunk {i}] {authors}, {year} | Section: {section} | "
            f"Similarity: {similarity:.4f}\n{text}"
        )
    return "\n\n".join(parts)


def _extract_json_block(text: str) -> str:
    """Return the JSON object substring from a model response.

    Strips markdown code fences (```json ... ```), then grabs the first
    `{...}` block. Raises JudgeParseError if none is present.
    """
    cleaned = re.sub(r"```(?:json)?", "", text)
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise JudgeParseError("No JSON object found in response")
    return match.group()


# Judge output-token ceiling. Higher than the old 8192 because the binary judge's
# DECOMPOSED responses are large — faithfulness alone can emit 40+ atomic claims
# (~4.5k output tokens), and Gemini 2.5 thinking tokens (~4.8k) count against the
# same budget, so 8192 truncated the JSON mid-array. This is a ceiling, not a
# target: billing is per token generated, so raising it costs nothing and only
# prevents truncation. Scoped to the judge (RAG generation sets its own limit).
_JUDGE_MAX_TOKENS = 16384


async def _generate_with_retry(
    prompt: str,
    system: str,
    judge_model: str | None = None,
    max_retries: int = 3,
    temperature: float = 0.0,
) -> str:
    """Generate with retry on transient transport errors (429 + 5xx).

    Backoff: 2s, 5s, 10s.

    Dispatches by `judge_model` prefix: `claude-*` routes to the Anthropic
    provider, anything else to Gemini (the model is threaded into Gemini's
    `generate` so a specific variant is actually used). `judge_model=None`
    falls back to `config.LLM_MODEL` (the default Gemini judge).
    """
    delays = [2.0, 5.0, 10.0]
    model = judge_model or config.LLM_MODEL
    use_claude = model.startswith("claude-")

    for attempt in range(max_retries):
        try:
            if use_claude:
                return await anthropic_provider.generate(
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    max_tokens=_JUDGE_MAX_TOKENS,
                    model=model,
                )
            return await llm_provider.generate(
                prompt=prompt,
                system=system,
                temperature=temperature,
                max_tokens=_JUDGE_MAX_TOKENS,
                model=model,
            )
        except RuntimeError as e:
            err = str(e)
            if _is_retryable_error(err) and attempt < max_retries - 1:
                delay = delays[attempt]
                logger.warning(
                    f"Judge retryable error (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                raise

    # Should not reach here, but just in case
    raise RuntimeError("Max retries exceeded for judge generation")


# Temperatures used across parse-retry attempts. The judge runs at 0.0 for
# determinism, but Gemini at temp 0 tends to reproduce an identical (and
# identically-malformed) reply — so each retry nudges temperature up to sample
# a genuinely different response that has a chance of parsing.
_PARSE_RETRY_TEMPERATURES = [0.0, 0.3, 0.6]


async def _generate_and_parse(
    prompt: str,
    system: str,
    parse_fn,
    judge_model: str | None = None,
):
    """Generate a judge response and parse it, regenerating on parse failure.

    Transport errors (429/5xx) are retried inside `_generate_with_retry`.
    `JudgeParseError` (malformed/truncated JSON) triggers a fresh generation at
    a higher temperature. After all attempts are exhausted the final
    JudgeParseError propagates so the caller can apply its own fallback (an
    ERRORED metric, never a synthesized value).

    `parse_fn` maps a raw response string to the parsed result and must raise
    `JudgeParseError` when the response is unusable.
    """
    last_err: JudgeParseError | None = None
    for attempt, temperature in enumerate(_PARSE_RETRY_TEMPERATURES):
        response = await _generate_with_retry(
            prompt, system, judge_model, temperature=temperature
        )
        try:
            return parse_fn(response)
        except JudgeParseError as e:
            last_err = e
            logger.warning(
                f"Judge parse failed (attempt {attempt + 1}/"
                f"{len(_PARSE_RETRY_TEMPERATURES)}, temp={temperature}): {e}"
            )
            if attempt < len(_PARSE_RETRY_TEMPERATURES) - 1:
                await asyncio.sleep(2.0)

    assert last_err is not None
    raise last_err
