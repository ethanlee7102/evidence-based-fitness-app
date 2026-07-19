"""Measure the bundled deterministic assertions across the frozen fixture.

Runs `src/core/eval/deterministic_checks` (refusal grounding, citation-presence/
format, report-only verbatim copy) plus the item-1 citation-validity check over a
captured RAG-output fixture and prints one combined report:

    - refusal:  OOS cases that failed to refuse; answerable cases that falsely refused
    - format:   grounded answers missing any [Author, Year] citation
    - verbatim: longest-copied-span distribution + cases over the threshold (report-only)
    - citation: ungrounded [Author, Year] citations (from item 1)

Deterministic and offline — reads a FROZEN fixture (no generation, no LLM, no DB),
so it is safe to re-run any time and produces a stable artifact for the README /
methodology writeup. NOT a per-PR gate (the unit tests are); this is the
measurement, run by hand or in the scheduled eval pipeline (Phase 2.5 item 3).

Usage:
    python -m scripts.measure_deterministic
    python -m scripts.measure_deterministic --output results/deterministic_checks.json
    python -m scripts.measure_deterministic --verbatim-threshold 15
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from src.core.eval.deterministic_checks import DEFAULT_VERBATIM_WORDS, run_all
from src.core.eval.fixtures import CURRENT_FIXTURE, current_fixture_path


def measure(fixture_path: Path, verbatim_threshold: int) -> dict:
    data = json.loads(fixture_path.read_text())
    cases = data["cases"]

    refusal_failures = []          # OOS answered, or answerable falsely refused
    format_failures = []           # grounded answer with no citation
    citation_failures = []         # cases with ≥1 ungrounded citation
    verbatim_flagged = []          # copied span >= threshold (report-only)
    verbatim_dist: Counter = Counter()

    n_oos = n_grounded = total_ungrounded = 0

    for c in cases:
        checks = run_all(c, verbatim_threshold=verbatim_threshold)

        if checks.refusal.oos:
            n_oos += 1
        if checks.refusal.failure:
            refusal_failures.append({"id": c.get("id"), "failure": checks.refusal.failure})

        if checks.format.applicable:
            n_grounded += 1
        if checks.format.failure:
            format_failures.append({"id": c.get("id"), "failure": checks.format.failure})

        total_ungrounded += len(checks.citation.ungrounded)
        if checks.citation.ungrounded:
            citation_failures.append({
                "id": c.get("id"),
                "ungrounded": [u.raw for u in checks.citation.ungrounded],
            })

        verbatim_dist[checks.verbatim.longest_run] += 1
        if checks.verbatim.flagged:
            verbatim_flagged.append({
                "id": c.get("id"),
                "longest_run": checks.verbatim.longest_run,
                "span": checks.verbatim.span,
            })

    return {
        "fixture": fixture_path.name,
        "fixture_timestamp": data.get("metadata", {}).get("timestamp"),
        "cases_total": len(cases),
        "verbatim_threshold": verbatim_threshold,
        "refusal": {
            "oos_cases": n_oos,
            "failures": refusal_failures,
        },
        "format": {
            "grounded_cases": n_grounded,
            "missing_citation": format_failures,
        },
        "citation": {
            "ungrounded_total": total_ungrounded,
            "failures": citation_failures,
        },
        "verbatim_report_only": {
            "flagged_count": len(verbatim_flagged),
            "distribution": {str(k): v for k, v in sorted(verbatim_dist.items())},
            "flagged": sorted(verbatim_flagged, key=lambda x: -x["longest_run"]),
        },
    }


def _print(r: dict) -> None:
    print("=" * 72)
    print(f"DETERMINISTIC CHECKS  —  {r['fixture']}  ({r['fixture_timestamp']})")
    print("=" * 72)
    print(f"  cases: {r['cases_total']}")
    print("-" * 72)

    rf = r["refusal"]
    print(f"REFUSAL   ({rf['oos_cases']} OOS cases)")
    if rf["failures"]:
        for f in rf["failures"]:
            print(f"    FAIL [{f['id']}] {f['failure']}")
    else:
        print("    ok — OOS refused, answerable questions answered")

    fm = r["format"]
    print(f"FORMAT    ({fm['grounded_cases']} grounded answers require a citation)")
    if fm["missing_citation"]:
        for f in fm["missing_citation"]:
            print(f"    FAIL [{f['id']}] {f['failure']}")
    else:
        print("    ok — every grounded answer carries ≥1 citation")

    ci = r["citation"]
    print(f"CITATION  ({ci['ungrounded_total']} ungrounded citations)")
    for f in ci["failures"]:
        print(f"    [{f['id']}] {', '.join(repr(x) for x in f['ungrounded'])}")

    vb = r["verbatim_report_only"]
    print(f"VERBATIM  (report-only, threshold ≥{r['verbatim_threshold']} words) — "
          f"{vb['flagged_count']} case(s) flagged")
    for f in vb["flagged"]:
        print(f"    [{f['id']}] {f['longest_run']} words: {f['span']!r}")
    print("=" * 72)


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure deterministic checks over a frozen fixture")
    ap.add_argument("--fixture", type=str, default=None,
                    help=f"Fixture JSON to score (default: canonical {CURRENT_FIXTURE})")
    ap.add_argument("--verbatim-threshold", type=int, default=DEFAULT_VERBATIM_WORDS,
                    help=f"Verbatim word-run flag threshold (default {DEFAULT_VERBATIM_WORDS})")
    ap.add_argument("--output", type=str, help="Save report JSON to this path")
    args = ap.parse_args()

    fixture_path = Path(args.fixture) if args.fixture else current_fixture_path()
    report = measure(fixture_path, args.verbatim_threshold)
    _print(report)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        print(f"\nSaved report to {args.output}")


if __name__ == "__main__":
    main()
