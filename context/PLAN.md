# Flame Fitness — Plan Summary

**Portfolio builder for jump #1 (1 YOE).** Target list: Junior AI Engineer at Series A/B AI-first startups, OR Software Engineer / Backend Engineer doing AI work at Series A/B/C AI-using companies. Comp $110-150k base. Work quality is senior-tier — that's the differentiator at 1 YOE.

For canonical detail see:
- `context/PORTFOLIO-NARRATIVE.md` — full project framing, narrative for interviews/README
- `context/ROADMAP.md` — all decisions and the authoritative build order (decision #18)
- `context/CLAUDE.md` — tech stack, folder structure, current status
- `context/EVAL-PLAN.md` — eval validation experiment plan
- `context/FUTURE-PLANS.md` — v2 agentic design questions, deferred ideas

This file is intentionally short — the docs above are the source of truth. PLAN.md exists so a fresh reader sees the priority structure at a glance.

---

## Core Features

🎯 = headline portfolio feature (priority). 🟢 = substrate (functional, no further investment unless it unlocks AI work). ⏸️ = deferred (won't be demoed in AI-flavored interviews).

| Feature | Description | Status | Priority |
|---------|-------------|--------|----------|
| 🎯 RAG Chatbot v1 | Exercise science Q&A with cited research (195 papers, 5-metric eval, 4.57/5) | ✅ Complete | Headline |
| 🎯 Eval cross-validation | Run A (Haiku 4.5 judge) + Run B (Ragas) on cleaned dataset | ⏳ ROADMAP Phase 1 | Headline |
| 🎯 Retrieval improvements | Per-paper diversification + top_k=20 + FlashRank reranking + noise cleanup | ⏳ ROADMAP Phase 2 | Headline |
| 🎯 Agentic RAG v2 | LangGraph router → literature / workout data / exercise info branches + judge node | ⏳ ROADMAP Phase 3 | Headline |
| 🎯 Public artifacts | README "Tools Considered", interview-prep doc, one blog post | ⏳ during/after Phase 1 | Headline |
| 🟢 Auth & Onboarding | Supabase auth, 4-step profile setup | ✅ Complete | Substrate |
| 🟢 Workout Logging | Log exercises, sets, reps, weight, RPE | ✅ Complete | Substrate |
| 🟢 Exercise Library | 386 exercises, EMG-backed muscle mappings | ✅ Complete | Substrate |
| ⏸️ Progress Tracking | Volume per muscle, PRs, strength curves | Deferred (Phase 4) | Skipped — workout-data branch in v2 covers core analytics |
| ⏸️ Polish | Flame visualization, streaks, mobile improvements | Deferred (Phase 6) | Skipped — doesn't show in AI demo |

---

## Tech Stack (one-line)

React + TS + Vite (frontend) · FastAPI (backend) · Supabase Postgres + pgvector (DB) · Voyage AI embeddings · Gemini 2.5 Flash (LLM) · LangGraph (v2 orchestration) · LangSmith (trace UI) · Ragas (eval cross-validation). Selective LangChain user — see `PORTFOLIO-NARRATIVE.md` for the Build vs Buy framework.

---

## Deployment (when ready)

| Service | Platform | Notes |
|---|---|---|
| Frontend | Vercel | Auto-deploy from main |
| Backend | Railway or Render | Python FastAPI |
| Database | Supabase | Already running |

Not deployed yet. Defer until Phase 1+2 complete and the project is interview-ready.
