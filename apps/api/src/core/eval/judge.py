"""LLM-as-judge scoring for RAG evaluation.

5 metrics scored 1-5:
- Contextual Relevancy: Are retrieved chunks relevant to the question?
- Contextual Recall: Do chunks contain the expected facts?
- Contextual Precision: Are the most relevant chunks ranked highest?
- Answer Relevancy: Does the answer address the question?
- Faithfulness: Is the answer faithful to chunks (no hallucination)?

Two modes:
- Separate (default): 5 individual judge calls — maximum learning depth
- Combined (--combined): 1 call scores all 5 — faster iteration
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field

from src.core.llm_provider import generate
from src.utils.config import config

logger = logging.getLogger(__name__)


# --- Dataclasses ---


@dataclass
class MetricScore:
    """Score for a single evaluation metric."""

    score: int  # 1-5
    reasoning: str
    extra: dict = field(default_factory=dict)


@dataclass
class JudgeResult:
    """All 5 metric scores for a single test case."""

    contextual_relevancy: MetricScore
    contextual_recall: MetricScore
    contextual_precision: MetricScore
    answer_relevancy: MetricScore
    faithfulness: MetricScore

    def to_dict(self) -> dict:
        result = {}
        for name in [
            "contextual_relevancy",
            "contextual_recall",
            "contextual_precision",
            "answer_relevancy",
            "faithfulness",
        ]:
            ms: MetricScore = getattr(self, name)
            result[name] = {
                "score": ms.score,
                "reasoning": ms.reasoning,
                **({k: v for k, v in ms.extra.items()} if ms.extra else {}),
            }
        return result


# --- Prompt Templates ---

JUDGE_SYSTEM = """\
You are an expert evaluator for a Retrieval-Augmented Generation (RAG) system \
that answers exercise science questions using research papers. \
Score strictly according to the rubric. Return ONLY valid JSON.\
"""

CONTEXTUAL_RELEVANCY_PROMPT = """\
Evaluate whether the retrieved chunks are relevant to the user's question.

**Question:** {question}

**Retrieved Chunks:**
{chunks}

**Rubric (1-5):**
- 5: All chunks are highly relevant and directly address the question
- 4: Most chunks are relevant, with minor tangential content
- 3: About half the chunks are relevant
- 2: Most chunks are only loosely related
- 1: Chunks are mostly irrelevant to the question

Return JSON: {{"score": <1-5>, "reasoning": "<brief explanation>"}}\
"""

CONTEXTUAL_RECALL_PROMPT = """\
Evaluate whether the retrieved chunks contain the expected facts needed to \
answer the question.

**Expected Facts:**
{expected_facts}

**Retrieved Chunks:**
{chunks}

For each expected fact, determine if it is supported, partially supported, \
or not found in the chunks.

**Rubric (1-5):**
- 5: All expected facts are fully supported by the chunks
- 4: Most facts supported, one partially or missing
- 3: About half the facts are supported
- 2: Most facts are missing or only partially supported
- 1: None or almost none of the expected facts are found

Return JSON:
{{
    "score": <1-5>,
    "reasoning": "<brief explanation>",
    "fact_coverage": {{
        "<fact text>": "supported" | "partial" | "not_found"
    }}
}}\
"""

CONTEXTUAL_PRECISION_PROMPT = """\
Evaluate whether the most relevant chunks are ranked highest (appear first).

**Question:** {question}

**Retrieved Chunks (in retrieval order, with similarity scores):**
{chunks}

**Rubric (1-5):**
- 5: The most relevant chunks are clearly ranked at the top
- 4: Top chunks are mostly the most relevant, minor ordering issues
- 3: Ranking is mixed — some relevant chunks are buried lower
- 2: The most relevant chunks appear near the bottom
- 1: Ranking is inverted — least relevant chunks appear first

Return JSON: {{"score": <1-5>, "reasoning": "<brief explanation>"}}\
"""

ANSWER_RELEVANCY_PROMPT = """\
Evaluate whether the generated answer directly and completely addresses \
the user's question.

**Question:** {question}

**Answer:** {answer}

**Rubric (1-5):**
- 5: Answer directly and completely addresses the question with clear structure
- 4: Answer mostly addresses the question, minor gaps
- 3: Answer partially addresses the question, misses key aspects
- 2: Answer is tangentially related but doesn't really answer the question
- 1: Answer is off-topic or incoherent

Return JSON: {{"score": <1-5>, "reasoning": "<brief explanation>"}}\
"""

FAITHFULNESS_PROMPT = """\
Evaluate whether the generated answer is faithful to the retrieved chunks. \
Check that every factual claim in the answer is supported by the chunks. \
Identify any unsupported or hallucinated claims.

**Retrieved Chunks:**
{chunks}

**Answer:** {answer}

**Rubric (1-5):**
- 5: Every claim in the answer is directly supported by the chunks, zero hallucination
- 4: Almost all claims supported, one minor unsupported detail
- 3: Most claims supported but some notable unsupported claims
- 2: Many claims are not supported by the chunks
- 1: The answer is mostly hallucinated / not grounded in the chunks

Return JSON:
{{
    "score": <1-5>,
    "reasoning": "<brief explanation>",
    "unsupported_claims": ["<claim 1>", "<claim 2>"]
}}\
"""

COMBINED_PROMPT = """\
Evaluate this RAG system output across all 5 metrics. Score each 1-5 \
according to the rubrics below.

**Question:** {question}

**Expected Facts:**
{expected_facts}

**Retrieved Chunks (in retrieval order, with similarity scores):**
{chunks}

**Generated Answer:** {answer}

**Metrics and Rubrics:**

1. **Contextual Relevancy** — Are the retrieved chunks relevant to the question?
   5=all highly relevant, 4=most relevant, 3=half relevant, 2=mostly loose, 1=irrelevant

2. **Contextual Recall** — Do chunks contain the expected facts?
   5=all facts found, 4=most found, 3=half found, 2=most missing, 1=none found

3. **Contextual Precision** — Are the most relevant chunks ranked highest?
   5=best at top, 4=mostly correct order, 3=mixed, 2=relevant buried, 1=inverted

4. **Answer Relevancy** — Does the answer address the question?
   5=complete direct answer, 4=mostly addresses, 3=partial, 2=tangential, 1=off-topic

5. **Faithfulness** — Is the answer faithful to chunks (no hallucination)?
   5=zero hallucination, 4=one minor unsupported detail, 3=some unsupported, \
2=many unsupported, 1=mostly hallucinated

Return JSON:
{{
    "contextual_relevancy": {{"score": <1-5>, "reasoning": "..."}},
    "contextual_recall": {{"score": <1-5>, "reasoning": "...", "fact_coverage": {{"<fact>": "supported|partial|not_found"}}}},
    "contextual_precision": {{"score": <1-5>, "reasoning": "..."}},
    "answer_relevancy": {{"score": <1-5>, "reasoning": "..."}},
    "faithfulness": {{"score": <1-5>, "reasoning": "...", "unsupported_claims": []}}
}}\
"""


# --- Helpers ---


def _format_chunks_for_judge(chunks: list) -> str:
    """Format chunks with metadata and full text for judge prompts."""
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


def extract_score(response: str) -> tuple[int, str, dict]:
    """Extract score, reasoning, and extras from judge response.

    Tries JSON parsing first, falls back to regex for 'Score: X' pattern.
    Returns (score, reasoning, extra_dict).
    """
    # Try JSON parsing first
    try:
        # Find JSON in response (may have surrounding text)
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            data = json.loads(json_match.group())
            score = int(data.get("score", 0))
            reasoning = data.get("reasoning", "")
            extra = {
                k: v
                for k, v in data.items()
                if k not in ("score", "reasoning")
            }
            if 1 <= score <= 5:
                return score, reasoning, extra
    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    # Regex fallback
    score_match = re.search(r"[Ss]core:\s*(\d)", response)
    if score_match:
        score = int(score_match.group(1))
        if 1 <= score <= 5:
            return score, response, {}

    logger.warning(f"Could not extract score from response: {response[:200]}")
    return 3, f"Score extraction failed. Raw: {response[:500]}", {}


async def _generate_with_retry(
    prompt: str,
    system: str,
    judge_model: str | None = None,
    max_retries: int = 3,
) -> str:
    """Generate with retry on 429/503 errors.

    Backoff: 2s, 5s, 10s.
    """
    delays = [2.0, 5.0, 10.0]
    model = judge_model or config.LLM_MODEL

    for attempt in range(max_retries):
        try:
            return await generate(
                prompt=prompt,
                system=system,
                temperature=0.0,
                max_tokens=8192,
            )
        except RuntimeError as e:
            err = str(e)
            if ("429" in err or "503" in err) and attempt < max_retries - 1:
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


# --- Individual Judge Functions ---


async def judge_contextual_relevancy(
    question: str,
    chunks: list,
    judge_model: str | None = None,
) -> MetricScore:
    """Score how relevant the retrieved chunks are to the question."""
    prompt = CONTEXTUAL_RELEVANCY_PROMPT.format(
        question=question,
        chunks=_format_chunks_for_judge(chunks),
    )
    response = await _generate_with_retry(prompt, JUDGE_SYSTEM, judge_model)
    score, reasoning, extra = extract_score(response)
    return MetricScore(score=score, reasoning=reasoning, extra=extra)


async def judge_contextual_recall(
    expected_facts: list[str],
    chunks: list,
    judge_model: str | None = None,
) -> MetricScore:
    """Score whether chunks contain the expected facts."""
    facts_text = "\n".join(f"- {fact}" for fact in expected_facts)
    prompt = CONTEXTUAL_RECALL_PROMPT.format(
        expected_facts=facts_text,
        chunks=_format_chunks_for_judge(chunks),
    )
    response = await _generate_with_retry(prompt, JUDGE_SYSTEM, judge_model)
    score, reasoning, extra = extract_score(response)
    return MetricScore(score=score, reasoning=reasoning, extra=extra)


async def judge_contextual_precision(
    question: str,
    chunks: list,
    judge_model: str | None = None,
) -> MetricScore:
    """Score whether the most relevant chunks are ranked highest."""
    prompt = CONTEXTUAL_PRECISION_PROMPT.format(
        question=question,
        chunks=_format_chunks_for_judge(chunks),
    )
    response = await _generate_with_retry(prompt, JUDGE_SYSTEM, judge_model)
    score, reasoning, extra = extract_score(response)
    return MetricScore(score=score, reasoning=reasoning, extra=extra)


async def judge_answer_relevancy(
    question: str,
    answer: str,
    judge_model: str | None = None,
) -> MetricScore:
    """Score how well the answer addresses the question."""
    prompt = ANSWER_RELEVANCY_PROMPT.format(
        question=question,
        answer=answer,
    )
    response = await _generate_with_retry(prompt, JUDGE_SYSTEM, judge_model)
    score, reasoning, extra = extract_score(response)
    return MetricScore(score=score, reasoning=reasoning, extra=extra)


async def judge_faithfulness(
    chunks: list,
    answer: str,
    judge_model: str | None = None,
) -> MetricScore:
    """Score whether the answer is faithful to the chunks (no hallucination)."""
    prompt = FAITHFULNESS_PROMPT.format(
        chunks=_format_chunks_for_judge(chunks),
        answer=answer,
    )
    response = await _generate_with_retry(prompt, JUDGE_SYSTEM, judge_model)
    score, reasoning, extra = extract_score(response)
    return MetricScore(score=score, reasoning=reasoning, extra=extra)


# --- Combined Judge ---


async def judge_combined(
    question: str,
    expected_facts: list[str],
    chunks: list,
    answer: str,
    judge_model: str | None = None,
) -> JudgeResult:
    """Score all 5 metrics in a single LLM call."""
    facts_text = "\n".join(f"- {fact}" for fact in expected_facts)
    prompt = COMBINED_PROMPT.format(
        question=question,
        expected_facts=facts_text,
        chunks=_format_chunks_for_judge(chunks),
        answer=answer,
    )
    response = await _generate_with_retry(prompt, JUDGE_SYSTEM, judge_model)
    logger.debug(f"Combined judge raw response: {response[:500]}")

    # Parse the combined JSON response
    try:
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            raise ValueError("No JSON found in combined response")
        data = json.loads(json_match.group())
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Combined judge parse failed: {e}. Using fallback scores.")
        fallback = MetricScore(score=3, reasoning=f"Parse failed: {str(e)}")
        return JudgeResult(
            contextual_relevancy=fallback,
            contextual_recall=fallback,
            contextual_precision=fallback,
            answer_relevancy=fallback,
            faithfulness=fallback,
        )

    def _parse_metric(key: str) -> MetricScore:
        metric_data = data.get(key, {})
        if isinstance(metric_data, dict):
            score = int(metric_data.get("score", 3))
            score = max(1, min(5, score))
            reasoning = metric_data.get("reasoning", "")
            extra = {
                k: v
                for k, v in metric_data.items()
                if k not in ("score", "reasoning")
            }
            return MetricScore(score=score, reasoning=reasoning, extra=extra)
        return MetricScore(score=3, reasoning=f"Missing {key} in response")

    return JudgeResult(
        contextual_relevancy=_parse_metric("contextual_relevancy"),
        contextual_recall=_parse_metric("contextual_recall"),
        contextual_precision=_parse_metric("contextual_precision"),
        answer_relevancy=_parse_metric("answer_relevancy"),
        faithfulness=_parse_metric("faithfulness"),
    )


# --- Dispatcher ---


async def judge_all(
    question: str,
    expected_facts: list[str],
    chunks: list,
    answer: str,
    combined: bool = False,
    inter_call_delay: float = 5.0,
    judge_model: str | None = None,
) -> JudgeResult:
    """Run all 5 judges. Dispatches to combined or separate mode.

    In separate mode, adds inter_call_delay between each judge call
    to stay under Gemini's 10 RPM free tier limit.
    """
    if combined:
        return await judge_combined(
            question, expected_facts, chunks, answer, judge_model
        )

    # Separate mode — 5 individual calls with delays
    cr = await judge_contextual_relevancy(question, chunks, judge_model)
    await asyncio.sleep(inter_call_delay)

    recall = await judge_contextual_recall(expected_facts, chunks, judge_model)
    await asyncio.sleep(inter_call_delay)

    cp = await judge_contextual_precision(question, chunks, judge_model)
    await asyncio.sleep(inter_call_delay)

    ar = await judge_answer_relevancy(question, answer, judge_model)
    await asyncio.sleep(inter_call_delay)

    faith = await judge_faithfulness(chunks, answer, judge_model)

    return JudgeResult(
        contextual_relevancy=cr,
        contextual_recall=recall,
        contextual_precision=cp,
        answer_relevancy=ar,
        faithfulness=faith,
    )
