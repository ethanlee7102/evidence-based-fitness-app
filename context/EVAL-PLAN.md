# RAG Eval Validation Plan

A two-stage validation experiment for the existing custom eval pipeline. Goal: characterize how my custom judge behaves relative to (a) the same prompts with a different judge model, and (b) the industry-standard implementation. Produce defensible numbers backing the choice to keep custom for eval while using frameworks elsewhere.

---

## Motivation

The current eval (`src/core/eval/`) uses Gemini 2.5 Flash to judge a Gemini 2.5 Flash RAG pipeline. Post-expansion score is 4.57/5 on 100 cases. Two questions worth answering with data:

1. **Same-model effect** — does swapping the judge model materially change the scores? (If yes, my baseline is noisier than it looks.)
2. **Implementation agreement** — does Ragas's industry-standard implementation produce similar scores on the same data? (If yes, custom is validated; if no, the disagreements reveal something useful about either my prompts or Ragas's.)

This is *characterization*, not *defense*. I'm not trying to argue against using Ragas — I'm using my custom eval and want to know how it behaves. The narrative being supported: "I use frameworks where they solve real problems (orchestration, trace UI) and went deep on eval because that's where production tooling is weakest. Here are the numbers showing my judge isn't drifting from the industry baseline."

---

## Experimental Design

Two runs on the **same 100 test cases**, with one optional third:

| Run | Implementation | Judge model | Purpose |
|---|---|---|---|
| Run 0 | Custom (existing) | Gemini 2.5 Flash | Baseline, already exists |
| **Run A** | Custom (existing) | Claude Haiku 4.5 | Isolates *model bias* — same prompts, different model |
| **Run B** | Ragas | Gemini 2.5 Flash | Isolates *implementation differences* — same model, different implementation |
| Run C *(optional)* | Ragas | Claude Haiku 4.5 | Full cross-check. Skip unless A and B both surface something interesting |

**Why drop the original Run C as default**: a portfolio project doesn't need research-grade 2×2 rigor. Run A answers the model-bias question. Run B answers the implementation question. Run C only adds value if the first two disagree in a confusing way — then it becomes a useful tiebreaker. Otherwise it's polish that doesn't change the story.

**Model choice rationale**: Claude Haiku 4.5 over Claude Sonnet 4.6 or GPT-4o because (a) a cheaper model agreeing with the custom Gemini judge is methodologically as strong as an expensive one agreeing — it shows robustness across capability tiers, not just model families; (b) ~$1.50-3 per run vs ~$5-8 for Sonnet; (c) faster wall-clock (~30-40 min vs 60-90 min). The Anthropic ecosystem alignment still holds. Different model family from Gemini preserved.

---

## Implementation

### 1. Add Claude provider for judge calls

Current state: `src/core/eval/judge.py` imports `generate` from `src/core/llm_provider.py`, which is Gemini-only. **⚠️ Bug found 2026-05-30 (must fix here): `generate()` has NO `model` parameter — it reads the model from `config.LLM_MODEL` internally. So `_generate_with_retry`'s `judge_model` arg is currently accepted but SILENTLY IGNORED, and `--judge-model` does nothing (it never even swapped Gemini variants — that earlier note was wrong).** Any cross-model work must first make the model actually selectable.

Changes:
- Add `src/core/anthropic_provider.py` — `generate()` mirroring the Gemini provider signature (`prompt`, `system`, `temperature`, `max_tokens`). Shared `httpx.AsyncClient`, cleaned up in `app.py` lifespan hook. Retry on 429/500/503 with exponential backoff.
- **First make the model selectable**: add a `model` param to `llm_provider.generate()` (defaulting to `config.LLM_MODEL`) and pass it through `_get_gemini_url`. Without this, dispatch can't work.
- Refactor `_generate_with_retry` in `judge.py` to dispatch based on model ID prefix (`gemini-*` → Gemini `generate`, `claude-*` → Anthropic `generate`), threading `judge_model` through. Keep the existing retry/backoff + the parse-retry wrapper (`_generate_and_parse`) already in place.
- Add `ANTHROPIC_API_KEY` to `config.py` (lazy validation — only required when a Claude judge is invoked).
- Update `--judge-model` help text in `evaluate_rag.py`.
- Verify after wiring: `--judge-model gemini-2.5-pro` (or any non-default Gemini) on one case actually changes which model is called (confirms the dispatch works before spending on Run A).

### 2. Run A — custom + Claude (the high-ROI run)

```bash
cd apps/api
python -m scripts.evaluate_rag \
  --combined \
  --judge-model claude-haiku-4-5 \
  --output results/run_a_custom_claude.json \
  --verbose
```

Same 100 cases, same prompts, same combined mode. Only variable: judge model.

### 3. Ragas integration

- Add `ragas` to `requirements.txt`. Pin version.
- New file: `src/core/eval/ragas_runner.py` — wraps Ragas's `evaluate()` over the same dataset format used by the custom runner. Map the 5 Ragas metrics to the existing 5 metric names (`contextual_relevancy`, `contextual_recall`, `contextual_precision`, `answer_relevancy`, `faithfulness`).
- Configure Ragas's LLM backend with Gemini for Run B.
- New CLI script: `scripts/evaluate_rag_ragas.py` with `--judge-model` and `--output` flags, parallel to the existing CLI.
- Match rate-limiting: 7s between cases (Gemini free-tier safe), 5s between metric calls. Ragas's default concurrency is too aggressive for Tier 1 quotas.

### 4. Run B — Ragas + Gemini

```bash
python -m scripts.evaluate_rag_ragas \
  --judge-model gemini-2.5-flash \
  --output results/run_b_ragas_gemini.json
```

### 5. (Optional) Run C — Ragas + Claude

Only if A and B disagree in ways that need disambiguation. Same script as Run B, `--judge-model claude-haiku-4-5`.

### 6. Analysis script

New file: `scripts/analyze_eval_agreement.py`. Loads available runs (Run 0 baseline + A + B [+ C]), produces:

- **Per-metric mean comparison** — table of mean scores across runs.
- **Pearson correlation** between runs, per metric. Target: >0.85 = high agreement.
- **Within-1-point agreement rate** — for each case, what % of metric scores agree within ±1.0 across runs.
- **Disagreement cases** — list cases where any two runs differ by >1.5 on any metric. These are the *interesting* failures — they reveal which metric/judge combinations are fragile.
- **Outlier-metric detection** — flag any metric where one run is >0.3 from the others. Likely indicates either a prompt issue or a model-specific bias.

---

## Deliverables

1. **JSON result files** in `apps/api/results/` for whichever runs are executed.
2. **Analysis report** in `apps/api/results/eval_agreement_analysis.md` — generated by the analysis script. Tables + commentary.
3. **README section** in the project README — "Evaluation Methodology" with:
    - One paragraph on why custom + when to validate.
    - Headline numbers (correlation across runs).
    - A short note on what each metric is most stable on.
4. **Interview answer document** in `context/EVAL-INTERVIEW-NOTES.md` — short, written for spoken delivery. Three paragraphs: what I built, what I measured, what I learned.

---

## Cost & Time Estimate

| Step | Time | API cost |
|---|---|---|
| Anthropic provider + judge dispatch | 0.5 day | — |
| Run A (custom + Claude Haiku 4.5) | runs unattended | ~$1.50-3 (Haiku 4.5 judge on 100 cases combined mode, ~200 calls) |
| Ragas integration + script | 1-1.5 days | — |
| Run B (Ragas + Gemini) | runs unattended | $0 (Gemini paid tier 1, well under cap) |
| Analysis script + report | 0.5 day | — |
| README + interview-notes writeup | 0.5 day | — |
| **Total** | **~2-2.5 days active work** | **~$1.50-3** |
| *Optional Run C* | *+0.5 day setup, runs unattended* | *+$1.50-3 (Haiku 4.5)* |

Wall-clock for the runs themselves: Haiku 4.5 runs ~30-40 min in combined mode (faster than Sonnet). Run unattended.

---

## Run B Status: Committed

Original plan staged Run B as conditional on Run A results. **Updated 2026-05-10**: Run B is committed regardless of Run A outcome.

Rationale: Run A and Run B answer different questions. Run A measures judge model bias (custom-Gemini vs custom-Claude). Run B measures implementation differences (custom-Gemini vs Ragas-Gemini). Both are independently valuable for the interview narrative, and committing to both upfront produces a tighter story ("I characterized my custom eval against both a different model and the industry-standard implementation") than staging.

Cost of committing: +1-1.5 days of Ragas integration work, +~$0 Gemini cost (paid tier 1 well under cap).

---

## Open Decisions

1. **Claude model ID** — `claude-haiku-4-5` chosen for cost ($1.50-3/run vs ~$5-8 for Sonnet 4.6) with equivalent methodological strength. Sonnet 4.6 is the fallback if Haiku produces noisy or inconsistent scoring.
2. **Ragas metric semantics** — Ragas's `context_recall` requires ground-truth answers; my test dataset has `expected_facts` which is close but not identical. Need to decide: (a) use `expected_facts` joined into a synthetic ground-truth string, or (b) write ground-truth answers for the 100 cases (~2 hours of manual work). Option (b) is cleaner but slower. Start with (a), upgrade to (b) only if Run B produces noisy `context_recall` scores.
3. **Whether to also re-run Run 0 for freshness** — Run 0 is from 2026-03-19. Corpus hasn't changed since then, so probably skip. Re-run only if any other variable (chunking, top_k, prompts) has changed.

---

## Out of Scope

- Adding more test cases. 100 is sufficient.
- Replacing the production judge. Custom stays in place.
- Multi-shot prompting or judge ensembling.
- GPT-4o as a third judge model.
- Run C unless the first two motivate it.

---

## Narrative Fit

This plan supports the broader portfolio story: "I use LangChain/LangGraph at work and for v2 orchestration here, and I use Phoenix on top of my custom trace storage for live debugging. Where I went deep custom is the part the frameworks don't solve well — evaluation. Here's how I validated that the custom judge isn't drifting from the industry-standard tool."

That story works regardless of interviewer type. It doesn't require committing to a "build everything from primitives" stance that would conflict with day-job framework usage. The eval is the differentiator; orchestration and observability use the right tools for the job.

---

## Why This Plan Is Defensible

Run A directly answers "how do you know your judge isn't biased toward the model it's judging?" with a number, not a hand-wave. Run B answers "why custom over Ragas?" with comparison data. The optional Run C exists for when the first two disagree confusingly — it's a tiebreaker, not load-bearing. The staged decision point prevents over-investing in rigor a portfolio project doesn't need. Every deliverable maps to a question an interviewer would actually ask.
