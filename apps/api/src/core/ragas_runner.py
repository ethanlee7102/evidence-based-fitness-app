"""Run B — Ragas evaluation over a frozen RAG-output fixture (all-Gemini stack).

Lives OUTSIDE the `src.core.eval` package on purpose: that package's
`__init__.py` eagerly imports the live RAG pipeline (-> supabase), which isn't
installed in the isolated `venv-ragas`. This module imports only Ragas, the
Gemini LangChain wrappers, and the lightweight `config` — plus `report.py`,
loaded standalone via importlib so it doesn't drag the package `__init__` in.

What it does: read the fixture produced by `scripts.capture_rag_fixture`, score
each in-scope case with Ragas's 5 metrics (Gemini judge + Gemini embeddings),
and emit a report in the SAME schema as the custom judge so the two are
directly comparable.

Design decisions (see context/EVAL-PLAN.md §3):
  - Same frozen fixture as the custom judge -> isolates implementation, not
    re-generation, as the only difference.
  - Native 0-1 scores, NOT rescaled to the custom judge's 1-5. The metrics
    differ in definition; reconciliation happens in the analysis layer.
  - All-Gemini backend (judge + embeddings) keeps Run B a clean "same model,
    different implementation" comparison against the Gemini custom judge.

Metric mapping (Ragas result column -> our metric key):
  nv_context_relevance                  -> contextual_relevancy
  context_recall                        -> contextual_recall
  llm_context_precision_with_reference  -> contextual_precision
  answer_relevancy                      -> answer_relevancy
  faithfulness                          -> faithfulness
"""

import importlib.util
import logging
import time
import warnings
from pathlib import Path

# Ragas 0.4 warns that importing metrics from `ragas.metrics` (legacy) will move
# to `ragas.metrics.collections` in v1.0. The legacy evaluate() API is still the
# supported path in 0.4.3, so silence the noise.
warnings.filterwarnings("ignore", category=DeprecationWarning, module="ragas")

import ragas  # noqa: E402
from ragas import EvaluationDataset, SingleTurnSample, evaluate  # noqa: E402
from ragas.embeddings import LangchainEmbeddingsWrapper  # noqa: E402
from ragas.llms import LangchainLLMWrapper  # noqa: E402
from ragas.metrics import (  # noqa: E402
    ContextRelevance,
    Faithfulness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
    ResponseRelevancy,
)
from ragas.run_config import RunConfig  # noqa: E402

from langchain_google_genai import (  # noqa: E402
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)

from src.utils.config import config  # noqa: E402

logger = logging.getLogger(__name__)

# Gemini's current embedding model. (text-embedding-004 returns 404 on this
# API key/version; gemini-embedding-001 is the available all-Gemini option.)
# Only used by ResponseRelevancy to embed short question strings — never
# touches retrieval, so the exact model is low-stakes.
DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"
RAGAS_TIMEOUT_S = 180


# --- Reuse the custom pipeline's aggregation, without the package __init__ ---

def _load_report_module():
    """Load src/core/eval/report.py standalone (bypasses eval/__init__.py).

    report.py has no intra-package imports, so this is safe and gives us the
    EXACT same compute_aggregates/print_summary the custom judge uses —
    keeping the two reports apples-to-apples.
    """
    report_path = Path(__file__).resolve().parent / "eval" / "report.py"
    spec = importlib.util.spec_from_file_location("eval_report_standalone", report_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report = _load_report_module()


# --- Gemini backends ---------------------------------------------------------

def _safety_settings():
    """Disable Gemini content filters so judging isn't silently blocked.

    Exercise-science / medical text can trip default safety thresholds, which
    would surface as NaN scores. Returns None if the enums aren't importable
    (older/newer langchain-google-genai), in which case defaults apply.
    """
    try:
        from langchain_google_genai import HarmBlockThreshold, HarmCategory

        return {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    except Exception:  # noqa: BLE001
        logger.warning("Could not import Gemini safety enums; using defaults.")
        return None


def build_judge(judge_model: str) -> LangchainLLMWrapper:
    chat = ChatGoogleGenerativeAI(
        model=judge_model,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0.0,
        safety_settings=_safety_settings(),
    )
    return LangchainLLMWrapper(chat)


def build_embeddings(embedding_model: str) -> LangchainEmbeddingsWrapper:
    emb = GoogleGenerativeAIEmbeddings(
        model=embedding_model,
        google_api_key=config.GOOGLE_API_KEY,
    )
    return LangchainEmbeddingsWrapper(emb)


def build_metrics(llm, embeddings) -> list[tuple[str, object]]:
    """Return [(our_metric_key, ragas_metric_instance), ...] in report order."""
    return [
        ("contextual_relevancy", ContextRelevance(llm=llm)),
        ("contextual_recall", LLMContextRecall(llm=llm)),
        ("contextual_precision", LLMContextPrecisionWithReference(llm=llm)),
        ("answer_relevancy", ResponseRelevancy(llm=llm, embeddings=embeddings)),
        ("faithfulness", Faithfulness(llm=llm)),
    ]


# --- Helpers -----------------------------------------------------------------

def _is_oos(case: dict) -> bool:
    return "out-of-scope" in case.get("tags", [])


def _rag_result_stub(case: dict) -> dict:
    """Minimal rag_result dict for schema parity with the custom report
    (print_summary reads grounded for the out-of-scope section)."""
    return {
        "grounded": case.get("grounded"),
        "chunks_retrieved": len(case.get("chunks", [])),
        "answer": case.get("answer", ""),
    }


def _result_entry(case: dict, scores: dict | None, overall: float | None) -> dict:
    return {
        "id": case["id"],
        "question": case["question"],
        "category": case.get("category"),
        "difficulty": case.get("difficulty", "unknown"),
        "tags": case.get("tags", []),
        "scores": scores,
        "overall_score": overall,
        "rag_result": _rag_result_stub(case),
        "error": None,
    }


# --- Main entry point --------------------------------------------------------

def run_ragas_eval(
    fixture: dict,
    judge_model: str,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    max_workers: int = 4,
    verbose: bool = False,
) -> dict:
    """Score a frozen fixture with Ragas; return a report in the custom schema."""
    cases = fixture.get("cases", [])
    fixture_meta = fixture.get("metadata", {})

    llm = build_judge(judge_model)
    embeddings = build_embeddings(embedding_model)
    pairs = build_metrics(llm, embeddings)
    metrics = [m for _, m in pairs]
    name_to_key = {m.name: key for key, m in pairs}

    # Build dataset from in-scope cases only; OOS cases have no reference and a
    # refusal answer, matching the custom runner which skips judging them.
    samples: list[SingleTurnSample] = []
    scored_cases: list[dict] = []
    for case in cases:
        if _is_oos(case):
            continue
        contexts = [c.get("chunk_text", "") for c in case.get("chunks", [])]
        samples.append(
            SingleTurnSample(
                user_input=case["question"],
                response=case.get("answer", ""),
                retrieved_contexts=contexts,
                reference="\n".join(case.get("expected_facts", [])),
            )
        )
        scored_cases.append(case)

    print(
        f"\nRunning Ragas eval: {len(scored_cases)} in-scope cases "
        f"(judge={judge_model}, embeddings={embedding_model}, max_workers={max_workers})...\n"
    )

    start = time.time()
    dataset = EvaluationDataset(samples=samples)
    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(max_workers=max_workers, timeout=RAGAS_TIMEOUT_S),
    )
    duration = time.time() - start

    df = result.to_pandas()
    if len(df) != len(scored_cases):
        raise RuntimeError(
            f"Ragas returned {len(df)} rows for {len(scored_cases)} samples — "
            "row/case alignment broken."
        )

    # Map Ragas columns -> our keys, drop NaN (a metric that errored on a case).
    results: list[dict] = []
    failed = 0
    for i, case in enumerate(scored_cases):
        row = df.iloc[i]
        scores: dict = {}
        for col, key in name_to_key.items():
            if col not in df.columns:
                continue
            val = row[col]
            if val is None or val != val:  # NaN check
                continue
            scores[key] = {"score": round(float(val), 4)}
        metric_vals = [s["score"] for s in scores.values()]
        overall = round(sum(metric_vals) / len(metric_vals), 4) if metric_vals else None
        if not scores:
            failed += 1
            logger.warning(f"[{case['id']}] all Ragas metrics NaN — counted as failed.")
        if verbose:
            shown = ", ".join(f"{k}={v['score']}" for k, v in scores.items())
            print(f"  [{case['id']}] {shown or 'NO SCORES'}")
        results.append(_result_entry(case, scores or None, overall))

    # Append OOS cases (scores=None) for schema parity with the custom report.
    for case in cases:
        if _is_oos(case):
            results.append(_result_entry(case, None, None))

    return {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "implementation": "ragas",
            "ragas_version": ragas.__version__,
            # `model` = the RAG model that produced the frozen outputs (for the
            # report header); `judge_model` = the Ragas evaluator model.
            "model": fixture_meta.get("model"),
            "judge_model": judge_model,
            "embedding_model": embedding_model,
            "top_k": fixture_meta.get("top_k"),
            "similarity_threshold": fixture_meta.get("similarity_threshold"),
            "duration_s": round(duration, 1),
            "judge_mode": "ragas",
            "total_cases": len(cases),
            "scored_cases": len(scored_cases),
            "failed_cases": failed,
            "metrics_filter": None,
            "from_fixture": True,
            "score_scale": "0-1",
            "max_workers": max_workers,
            "metric_mapping": {m.name: key for key, m in pairs},
            "note": "Ragas native 0-1 scores (NOT rescaled to the custom 1-5). "
            "Ragas does not surface per-metric reasoning.",
        },
        "results": results,
    }
