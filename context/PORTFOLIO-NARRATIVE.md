# Portfolio Narrative — Flame Fitness RAG

The story to tell about this project. Source material for the README "Tools Considered and Rejected" section, interview talking points, and any blog posts.

---

## What This Project Actually Is

**This is a portfolio builder for jump #1 in a job search.** The project is a RAG / LLM / agentic AI system, demoed in the context of a workout logging app.

The workout logger is the substrate — it gives the AI features non-toy grounding (real user training data for the agentic workout-data branch, a domain with rich literature for the RAG corpus). But the *headline*, the *demo*, the *interview story*, and the *README* are all about the AI system: RAG pipeline, retrieval improvements, cross-validated evaluation, and agentic routing with LangGraph.

### Calibration: This Is For Jump #1 (1 YOE)

**Realistic target list (apply broadly across these):**
- **Junior AI Engineer / AI Engineer roles** at Series A/B AI-first startups — these are real and obtainable at 1 YOE *if* the portfolio is genuinely strong (which this one is built to be)
- **Software Engineer / Backend Engineer doing AI work** at Series A/B/C AI-using companies — slightly easier path with similar comp
- **Established companies adding AI capabilities** — mid-sized tech companies launching AI teams, looking for engineers who can ship full-stack with AI subsystems
- Realistic comp range $110-150k base in major markets, $100-130k elsewhere, with modest equity. Total comp $115-170k all-in.

**Not targeting (for this jump):**
- Frontier labs (Anthropic, OpenAI, DeepMind) — not realistic at 1 YOE regardless of portfolio strength
- Tier 1 stable companies (Stripe, Notion, Databricks) — competition too steep for jump #1
- Senior-level destination titles — interviewing for IC2/Mid-level (or Junior at AI-first startups) is realistic; "Senior" at the new company typically requires 3+ YOE before or there

**What I'm actually trying to do with jump #1:**
- Get a recognizable company name on the resume
- Land an AI-flavored role (Junior AI Engineer ideal; SWE-doing-AI as the broader funnel)
- Increase comp by 20-35% (realistic) rather than 50%+ (unrealistic)
- Work alongside more experienced engineers to accelerate skill development
- Position for jump #2 in 2-3 years (frontier lab / Tier 1 / Senior-level), which is where the bigger comp lives
- Move from "junior at unknown startup" to "junior/mid engineer with production AI experience at a recognized company"

### What This Calibration Means for the Project

**Critical clarification: realistic *hiring level* ≠ reduced *work quality*.** This portfolio is built to senior-quality depth and rigor. That's the whole point — going deep at 1 YOE is exactly what differentiates this portfolio from the typical Junior/Mid applicant pool, who mostly have tutorial-grade projects. The calibration below is about *self-positioning in interviews*, not about cutting corners in the work.

1. **Work quality**: senior-tier. Cross-validated eval, recall failure diagnostics, build-vs-buy reasoning for every component, public writing about the methodology, agentic architecture with judge + retry. None of this is optional. The signal *to the hiring manager* is "this 1-YOE engineer thinks like someone with 3-5 YOE" — that signal is what gets you past the junior-pool filter into the Junior AI Engineer offer pool.

2. **Self-positioning tone**: confident but not over-claiming. Not "founding engineer / senior architect" (that's overreach at 1 YOE and will be probed in interviews); also not "I followed a tutorial" (that's underselling and lands in the rejection pile). The right tone is *"I'm one year in and I built this because I wanted to understand what production AI actually looks like — here's what I learned, here's what I'd do differently."* That tone is irresistible to senior interviewers because it pattern-matches to "engineer on a steep trajectory" — exactly who they want to hire and grow.

3. **What to invest in deeply** (high portfolio ROI for this target):
   - AI/RAG/eval work — the actual differentiator across the entire Junior-to-Mid applicant pool
   - Agentic v2 (router + judge + retry across three retrieval branches) — the demo-worthy showcase
   - Public artifacts: README "Tools Considered" section, blog post, interview-prep doc — these get found in resume screens

4. **What to maintain but not extend** (substrate, not headline):
   - Workout logging UI/UX (Phase 4 progress charts, Phase 6 Flame visualization, Phase 3 leftover features) — already functional, won't be demoed in interviews. Full-stack engineering competence is shown by the *existence* of a working app, not by polishing it further. (This isn't cutting depth — it's spending depth where it shows up in the interview.)

5. **When to stop building and start applying**:
   - Past a certain point, additional portfolio polish has rapidly diminishing returns vs. networking, public writing, direct outreach, and interview reps
   - Target: cap remaining portfolio work at ~4-6 weekends (eval validation + retrieval improvements + agentic v2 MVP), then pivot while maintaining only critical fixes
   - Stopping early doesn't mean the work was shallow — it means the work *demonstrated* is strong, and additional polish doesn't increase the offer rate

6. **What this means for the dual target (Junior AI Engineer vs. SWE-doing-AI roles)**:
   - **Junior AI Engineer applications**: lead with the AI subsystem depth. Open with "I built a RAG system with cross-validated eval, then made it agentic with LangGraph." The full-stack app is supporting context.
   - **SWE-doing-AI applications**: lead with full-stack capability. Open with "I built a production-style full-stack workout app and went deep on the AI subsystem." The AI depth is the differentiator from typical SWE applicants.
   - Same portfolio, two emphases. Adjust resume bullets and cover-letter framing per application.

## The Headline

A production-style exercise science RAG chatbot inside a full-stack workout logging app. **Selective use of the LangChain ecosystem and custom implementations where understanding or fit matters.** Cross-validated with a custom LLM-as-judge eval framework against Ragas as the industry-standard reference — the system is measurable, debuggable, and every component choice has a defensible reason behind it.

The agentic v2 extends this with a LangGraph router that combines literature search, user workout data analysis, and structured exercise reference into unified answers — the kind of system that needs three fundamentally different retrieval methods, justifying the router as architecture rather than a workaround.

**What this signals to a hiring manager:** an engineer with one year of production experience who has gone substantially deeper than the typical junior/mid applicant — measurable improvements driven by real evaluation, deliberate framework choices, and a working full-stack app to demonstrate end-to-end engineering competence. The signal isn't "I'm already senior"; it's *"I'm 1 YOE but I think like someone with 3-5"* — exactly the trajectory signal that gets a junior engineer hired into a Junior AI Engineer role at a Series A/B AI-first startup, or into a Software Engineer (AI) role at a larger company.

## The Build vs Buy Decision Framework

The single most important meta-pattern in this project: every component is either custom or framework, with a clear reason.

### Built custom where the value is in understanding or tight fit:

| Component | Why custom |
|---|---|
| **v1 RAG orchestration** | The retrieve-then-generate flow is ~50 lines of direct httpx. LangChain abstractions would hide what's actually happening. At v1 complexity, the abstraction overhead isn't earned. |
| **LLM-as-judge eval** | 5 hand-written metric prompts (contextual relevancy/recall/precision, answer relevancy, faithfulness). The only way to actually understand RAG quality measurement is to write the judge yourself. Reading Ragas's source teaches less than writing your own. |
| **Trace storage schema** | The `rag_traces` table is tied to specific failure modes: embedding/retrieval/generation latency split, grounded flag, rewritten query. Generic observability frameworks don't capture these. |
| **Ingestion pipeline** | Docling + pymupdf hybrid for academic-paper header detection using bbox spatial matching. Domain-specific to PMC papers; no off-the-shelf solution. |

### Used frameworks where they solve real problems:

| Component | Why framework |
|---|---|
| **`langchain-text-splitters`** | Chunking is solved. Reinventing recursive character splitting would teach nothing new. |
| **LangGraph (v2 agentic flow)** | 4-5 node state machine for router → retrieval → judge → retry. At this complexity, the framework's abstractions are earned. Also matches production stack at day job. |
| **LangSmith (trace UI)** | Building a trace UI would be wasted effort. Native LangGraph integration is free. Screenshot-worthy for the README. |
| **Ragas (eval cross-validation)** | Canonical reference implementation for RAG eval metrics. The right tool for "validate my custom judge against the industry standard." |
| **Voyage AI embeddings** | State-of-the-art retrieval quality at same price as OpenAI's text-embedding-3-large; 1024 dims fits pgvector HNSW natively without halfvec workarounds. |
| **Gemini 2.5 Flash** | Cheapest competitive LLM; SSE streaming via REST API straightforward. |
| **Supabase pgvector** | Reduces ops surface (one DB for auth + data + vectors), HNSW index supports million-chunk scale, RLS for multi-tenant. |

### Explicitly rejected:

| Component | Why rejected |
|---|---|
| **LangChain RAG orchestration in v1** | At ~50 lines of clear code, LangChain's `RetrievalQA` chain would *add* complexity, not remove it. v1 simple enough not to need it. |
| **DeepEval (eval framework)** | Its RAGAS submodule is a reimplementation, not the actual Ragas library — using it would weaken the "validated against industry standard" claim. Also: ships with telemetry-on-by-default, vendor-tied to Confident AI's commercial product, and methodologically harder to reproduce. |
| **Pinecone / Weaviate** | Adds an operational surface for marginal gains over pgvector at this scale. ~8k chunks doesn't need a dedicated vector DB. |
| **LangChain itself for v1 orchestration** | The pipeline is `retrieve → format prompt → generate`. Three functions. LangChain's `RunnableSequence` would add abstractions without removing work. |

---

## The Eval Validation Story

The single most differentiating part of this project. Most candidates have "I built RAG and it works." This is the version that says "I measured it, characterized it across two independent axes, and the numbers are defensible."

### Custom eval framework

- 5 metrics (contextual relevancy / recall / precision, answer relevancy, faithfulness), each with hand-written judge prompts that I can articulate and defend.
- 100 test cases across 10 categories with `expected_facts`, `expected_papers`, difficulty tags.
- Two judge modes (separate per-metric calls vs. combined-into-one) with rate-limit-aware orchestration for Gemini free tier.
- Persistent results in versioned JSON snapshots for trend tracking.
- Baseline (2026-03-19): 4.57/5 overall, 0 failures across 100 cases.

### Cross-validation experimental design

The eval framework is validated across two independent axes to demonstrate it's not just self-confirming:

**Axis 1 (judge model)**: same custom prompts, swap Gemini → Claude Haiku 4.5 as the judge. Isolates same-model bias. Answers "is my judge over-rewarding its own model's outputs?" Notably, choosing Haiku over Sonnet was a deliberate cost-conscious decision — a cheaper model agreeing with the custom judge is methodologically *stronger* than an expensive one agreeing because it demonstrates robustness across capability tiers, not just across model families.

**Axis 2 (implementation)**: same Gemini judge model, swap custom prompts → Ragas's implementation. Isolates implementation differences. Answers "does my custom judge agree with the industry-standard tool?"

This is a 2×2 design with the existing baseline filling one cell. Each disagreement is attributable to a specific axis — model bias or implementation differences — by comparing across pairs.

### Recall failure diagnostic

For the cases where the system scored Contextual Recall = 2 (worst), I ran a chunk-level forensic analysis:

1. Verified all 19 expected papers across the 9 failure cases exist in the corpus (zero corpus gaps).
2. Re-ran retrieval to see what chunks were actually surfaced.
3. Read source paper chunks end-to-end to find the verbatim answer chunks.
4. Cross-referenced against retrieved chunks to classify failures.

The dominant failure mode wasn't "wrong corpus" or "wrong tool" — it was **single-paper saturation**: the embedding similarity clusters all top-5 results within one paper, even when multiple on-topic papers exist. This points at a specific fix (per-paper diversification + reranking) rather than a generic "add more papers" or "fine-tune embeddings."

Output: a `RETRIEVAL-TARGET-CHUNKS.md` reference doc with verified chunk IDs that retrieval improvements should surface — a binary success metric independent of the LLM judge.

### Test dataset audit

In the chunk-level analysis, I also discovered some expected facts were test-authoring errors — claims that contradicted the source paper or weren't substantively made in it. Fixed 5 test cases (with `_edit_reason` metadata preserved for reproducibility). Now eval failures reflect real retrieval performance, not test noise.

---

## The Narrative Lines for Different Audiences

### For "tell me about this project" (30 seconds)
"I built an exercise science RAG chatbot grounded in 195 peer-reviewed papers, with a custom LLM-as-judge eval framework I built to measure quality at a level the standard tools don't. I went deep on the evaluation because that's where production RAG systems are typically weakest, and I cross-validated my custom eval against Ragas to make sure my metrics weren't self-confirming."

### For "why custom eval over Ragas?" (60 seconds)
"I started with custom for a few reasons. First, I wanted to actually understand what each metric measures — writing the judge prompts forces you to think hard about what 'faithfulness' or 'contextual recall' really means in your system, which Ragas's abstraction hides. Second, I wanted control over the rate limiting and combined-mode for Gemini free tier, which would have required Ragas customization anyway. But I didn't use 'custom' as a reason to skip the industry standard — I validated my custom judge against Ragas on the same 100 cases and used the comparison data to characterize my eval's behavior. Disagreements I traced to methodology differences (Ragas decomposes into atomic claims; mine evaluates holistically), not bugs."

### For "why LangGraph but not LangChain for v1?" (60 seconds)
"It comes down to whether the abstraction earns its complexity. v1 is `retrieve → format prompt → generate` — three functions. LangChain's `RetrievalQA` would *add* a layer, not remove one. v2 is a state machine with conditional retries and a judge node — LangGraph's abstractions are genuinely useful at that complexity. The rule I followed: framework where it solves a problem I'd otherwise have to solve, custom where the framework would obscure the system without saving work."

### For "what did you learn?" (60 seconds)
"The biggest surprise was the chunk-level diagnostic on my eval failures. I expected 'we need more papers' to be the answer. Reading every retrieval failure end-to-end showed the corpus had every expected paper — the failure was actually retrieval clustering chunks from one paper even when multiple on-topic papers existed. That changed my whole roadmap: instead of expanding the corpus, I prioritized per-paper diversification and cross-encoder reranking. Good evaluation didn't just tell me my system worked — it told me *what specifically to fix*, and saved me weeks of work on the wrong thing."

---

## What Makes This Different From "Tutorial RAG"

This is the list of things to make sure the README shows, because they're the differentiators:

1. **Measurable**: 100-case eval with 5 metrics, baseline tracked over time.
2. **Cross-validated**: judge tested across both different model (Claude) and different implementation (Ragas).
3. **Debuggable**: custom trace storage + LangSmith UI; per-eval-failure forensic analysis with verified target chunks.
4. **Honest about limitations**: documented test-authoring issues found during analysis, fixed with metadata preserved. README has a "what's not solved" section.
5. **Defensible build-vs-buy decisions**: every tool choice has a one-line rationale in the README; nothing is there because "the tutorial said so."
6. **Domain-aware**: ingestion pipeline is built for academic papers specifically (header hierarchy detection via bbox spatial matching), not generic.
7. **Copyright-aware**: CC-BY filter on corpus, LLM synthesizes rather than displaying verbatim chunks.

---

## What I'd Add Next (Interview "Future Work" Answer)

- **Per-paper diversification + cross-encoder reranking** — already prioritized based on the recall failure diagnostic. The biggest single retrieval improvement.
- **v2 agentic flow with LangGraph** — router classifies query intent (literature / workout data / exercise info), routes to specialized retrieval, judge node verifies the answer before returning.
- **Public blog post** on the cross-evaluator validation methodology — there isn't great public writing on how to validate a custom LLM-as-judge against the industry standard, and I have the data to make a real argument.

---

## The Meta-Lesson (For Reflective Interview Questions)

The most important thing I learned isn't technical — it's about *when to trust your own eval*. Building a custom judge was right for understanding. Validating against Ragas was right for credibility. But reading failure cases end-to-end was the thing that actually changed my engineering decisions. Numbers tell you whether something works; reading the failures tells you what to fix. Both matter, and most people skip the second part because it's slow grunt work.

The other meta-lesson: every framework or tool choice deserves a sentence of justification. I don't use LangChain for v1 orchestration because three functions don't need a framework. I do use LangGraph for v2 because state machines with conditional edges genuinely benefit from the abstraction. I do use Ragas for eval cross-validation because canonical references matter for validation work. None of these are dogma. Each is a deliberate decision I can defend.

That's the engineering pattern: not "build everything" or "buy everything" — *select correctly per component, and be able to articulate why.* This is the kind of thinking that gets a one-YOE engineer hired at mid-level rather than entry-level, and gets them promoted to senior once they're in.
