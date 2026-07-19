"""Measure citation grounding across the frozen 100-case fixture.

Runs the deterministic citation-validity checker (src/core/eval/citation_validity)
over a captured RAG-output fixture and reports:

    (ungrounded citations) / (total citations) across N cases

Deterministic and offline — reads a FROZEN fixture (no generation, no LLM, no DB),
so it is safe to re-run any time and produces a stable artifact for the README /
methodology writeup. NOT a per-PR gate (the unit tests are); this is the
measurement, run by hand or in the eval pipeline.

Usage:
    python -m scripts.measure_citation_validity
    python -m scripts.measure_citation_validity --output results/citation_validity.json
    python -m scripts.measure_citation_validity --fixture results/rag_outputs_fixture.json
"""

import argparse
import json
from pathlib import Path

from src.core.eval.citation_validity import check_answer
from src.core.eval.fixtures import CURRENT_FIXTURE, current_fixture_path


def measure(fixture_path: Path) -> dict:
    data = json.loads(fixture_path.read_text())
    cases = data["cases"]

    total_cites = 0
    total_ungrounded = 0
    total_indirect = 0
    total_page_mismatch = 0
    applicable_cases = 0
    findings = []  # cases with an ungrounded citation (the ones to inspect)
    page_findings = []  # cases with a report-only page mismatch

    for c in cases:
        res = check_answer(c.get("answer", ""), c.get("chunks", []))
        if not res.applicable:
            continue
        applicable_cases += 1
        total_cites += res.total
        total_ungrounded += len(res.ungrounded)
        total_indirect += res.indirect_count
        total_page_mismatch += len(res.page_mismatches)

        if res.ungrounded:
            findings.append({
                "id": c.get("id"),
                "grounded_flag": c.get("grounded"),
                "ungrounded": [
                    {"raw": u.raw, "author": u.author, "year": u.year} for u in res.ungrounded
                ],
            })
        if res.page_mismatches:
            page_findings.append({
                "id": c.get("id"),
                "citations": [
                    {"raw": p.raw, "pages": p.pages} for p in res.page_mismatches
                ],
            })

    return {
        "fixture": fixture_path.name,
        "fixture_timestamp": data.get("metadata", {}).get("timestamp"),
        "cases_total": len(cases),
        "cases_applicable": applicable_cases,
        "metric_ungrounded": f"{total_ungrounded}/{total_cites} ungrounded citations",
        "total_citations": total_cites,
        "ungrounded_count": total_ungrounded,
        "indirect_count": total_indirect,
        "page_mismatch_count": total_page_mismatch,
        "ungrounded_findings": findings,
        "page_mismatch_findings": page_findings,
    }


def _print(report: dict) -> None:
    print("=" * 72)
    print(f"CITATION VALIDITY  —  {report['fixture']}  ({report['fixture_timestamp']})")
    print("=" * 72)
    print(f"  cases:              {report['cases_applicable']} applicable / {report['cases_total']} total")
    print(f"  total citations:    {report['total_citations']}")
    print(f"  indirect (as-cited-in, validated against citing source): {report['indirect_count']}")
    print(f"  page mismatches (report-only): {report['page_mismatch_count']}")
    print(f"  UNGROUNDED:         {report['metric_ungrounded']}")
    print("-" * 72)
    if report["ungrounded_findings"]:
        print("Ungrounded citations to inspect (true fabrication vs. unhandled form):")
        for f in report["ungrounded_findings"]:
            for u in f["ungrounded"]:
                print(f"  [{f['id']}] {u['raw']!r}  (grounded_flag={f['grounded_flag']})")
    else:
        print("No ungrounded citations. Every cited paper was actually retrieved.")
    print("=" * 72)


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure citation grounding over a frozen fixture")
    ap.add_argument(
        "--fixture", type=str, default=None,
        help=f"Fixture JSON to score (default: the canonical {CURRENT_FIXTURE})",
    )
    ap.add_argument("--output", type=str, help="Save report JSON to this path")
    args = ap.parse_args()

    fixture_path = Path(args.fixture) if args.fixture else current_fixture_path()
    report = measure(fixture_path)
    _print(report)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        print(f"\nSaved report to {args.output}")


if __name__ == "__main__":
    main()
