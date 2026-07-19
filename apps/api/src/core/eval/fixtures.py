"""Canonical frozen RAG-output fixture — single source of truth.

The eval pipeline freezes RAG outputs (answers + retrieved chunks) into a
fixture JSON once, then every deterministic verifier scores that SAME artifact
(so a difference is a system difference, never a re-generation difference).
Multiple config-labeled fixtures accumulate in `results/` as A/B history; this
module names the ONE that represents the currently-shipped system.

Deterministic-check scripts (citation validity, and the sibling assertions
coming in Phase 2.5) import `CURRENT_FIXTURE` / `current_fixture_path()` from
here, so re-capturing the canonical fixture repoints exactly one line — and the
change shows up in the PR diff.
"""

from pathlib import Path

# The shipped retrieval config: Voyage rerank-2.5 + score-gated per-paper cap
# (sgnorm@0.15), captured 2026-06-29. Update this one line on a re-capture.
CURRENT_FIXTURE = "rag_outputs_fixture_sgnorm015_full.json"

# .../apps/api/src/core/eval/fixtures.py -> parents[3] == .../apps/api
RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"


def current_fixture_path() -> Path:
    """Absolute path to the canonical fixture (clone-safe, cwd-independent)."""
    return RESULTS_DIR / CURRENT_FIXTURE
