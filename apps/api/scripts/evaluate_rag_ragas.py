"""Run B — Ragas + Gemini evaluation CLI (parallel to scripts/evaluate_rag.py).

Runs in the ISOLATED venv-ragas. Scores a frozen RAG-output fixture (produced by
scripts.capture_rag_fixture in the main venv) with Ragas's 5 metrics and a
Gemini judge + Gemini embeddings, then writes a report in the same schema as the
custom judge so the two are directly comparable.

This script is self-contained: it does NOT import scripts.evaluate_rag (that
pulls the live RAG pipeline / supabase, which isn't installed here).

Usage:
    cd apps/api

    # Full Run B
    venv-ragas/bin/python -m scripts.evaluate_rag_ragas --output results/run_b_ragas_gemini.json

    # Smoke test on a few cases
    venv-ragas/bin/python -m scripts.evaluate_rag_ragas \
        --fixture results/_fixture_smoke.json --ids HYP-001 NUT-003 --verbose

    # Preview without running
    venv-ragas/bin/python -m scripts.evaluate_rag_ragas --dry-run
"""

import argparse
import json
import logging
from pathlib import Path

from src.core.ragas_runner import DEFAULT_EMBEDDING_MODEL, report, run_ragas_eval

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

API_DIR = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE = API_DIR / "results" / "rag_outputs_fixture.json"
DEFAULT_OUTPUT = API_DIR / "results" / "run_b_ragas_gemini.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run B — Ragas + Gemini RAG evaluation")
    parser.add_argument("--fixture", type=str, default=str(DEFAULT_FIXTURE))
    parser.add_argument("--ids", nargs="+", help="Score only specific case IDs")
    parser.add_argument("--judge-model", type=str, default="gemini-2.5-flash")
    parser.add_argument("--embedding-model", type=str, default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without running")
    return parser.parse_args()


def load_fixture(path: str, ids: list[str] | None = None) -> dict:
    """Load the fixture, optionally filtering cases by ID (keeps metadata)."""
    with open(path) as f:
        fixture = json.load(f)
    if ids:
        id_set = set(ids)
        cases = [c for c in fixture.get("cases", []) if c["id"] in id_set]
        missing = id_set - {c["id"] for c in cases}
        if missing:
            print(f"Warning: IDs not found in fixture: {missing}")
        fixture["cases"] = cases
    return fixture


def print_dry_run(fixture: dict, args: argparse.Namespace) -> None:
    cases = fixture.get("cases", [])
    oos = sum(1 for c in cases if "out-of-scope" in c.get("tags", []))
    scored = len(cases) - oos
    print("\nDRY RUN — Run B (Ragas + Gemini)")
    print(f"  Fixture: {Path(args.fixture).name} ({len(cases)} cases, {oos} out-of-scope)")
    print(f"  Scored: {scored} in-scope cases x 5 metrics")
    print(f"  Judge: {args.judge_model} | Embeddings: {args.embedding_model}")
    print(f"  max_workers: {args.max_workers}")
    print(f"  Output: {args.output}")
    print("  Note: each case fans out to several Gemini calls (Ragas decomposes")
    print("  claims/questions per metric), so expect well over 5 calls/case.\n")


def main() -> None:
    args = parse_args()

    fixture = load_fixture(args.fixture, args.ids)
    if not fixture.get("cases"):
        print("No cases to evaluate.")
        return

    if args.dry_run:
        print_dry_run(fixture, args)
        return

    report_dict = run_ragas_eval(
        fixture=fixture,
        judge_model=args.judge_model,
        embedding_model=args.embedding_model,
        max_workers=args.max_workers,
        verbose=args.verbose,
    )
    report_dict = report.compute_aggregates(report_dict)

    # Save first — don't lose results if printing crashes.
    if args.output:
        report.save_json_report(report_dict, args.output)
    report.print_summary(report_dict)


if __name__ == "__main__":
    main()
