# Flame Fitness — Future Plans

## Immediate Next

- ~~**Run baseline RAG eval**~~ ✅ Done — Overall 4.55/5, answer relevancy 5.0, faithfulness 4.8
- **Expand hypertrophy corpus** — Only 3 papers, scored lowest recall (2.5). Add 5-10 CC-BY hypertrophy papers from PMC Open Access (training volume, frequency, tempo, muscle-specific hypertrophy, eccentric training, etc.). Re-ingest and re-run eval to measure improvement.
- **Set eval thresholds** — Use baseline scores to set passing thresholds in `test_rag_eval.py`

---

## v2 Chatbot: Agentic RAG with Router

The v1 chatbot answers exercise science questions from research papers (Simple RAG). v2 adds the ability to analyze the user's own workout data alongside literature.

### Architecture

```
User question
      │
      ▼
   Router (LLM classifies intent)
      │
      ├── "literature question"  →  RAG Pipeline (reuse v1)
      │
      ├── "workout data question" →  SQL query against workout tables
      │                              (workouts, exercises, workout_sets)
      │
      └── "both" →  Run both, combine
                     ("Research says 10-20 sets/week. You're doing 14.")
```

- Literature = unstructured text → vector search (same as v1)
- Workout data = structured numbers → SQL queries (different retrieval method)
- Router justified because of fundamentally different data types
- Requires workout logger to be built first (needs data to query)

### Learning Remaining
- [ ] Agents & routing (deferred from v1 learning plan)

---

## v2 RAG Improvements (Deferred from v1)

- **Cross-encoder re-ranking** — Add re-ranking step after vector retrieval for better precision
- **Abstract-augmented retrieval** — Always include abstract of cited papers in prompt context, even if abstract chunk didn't make top-k. Gives LLM full-picture grounding.
- **Two-stage retrieval** — Search abstracts first to find relevant papers, then search chunks within those papers for specific evidence
- **Multi-turn evaluation** — Eval pipeline currently single-turn only; query rewriting already verified but not evaluated systematically
- **Expand eval dataset** — Currently 29 cases (expanded from 20); add more as corpus grows
- **Cross-model judge validation** — Use GPT-4o or Claude as alternative judges to detect same-model scoring bias (Gemini judging Gemini)
- **Async Supabase calls** — Wrap sync `supabase-py` calls in `asyncio.to_thread()` if latency becomes an issue under load

---

## Workout Logger (Main App Phase 3)

Database tables planned:
- `exercises` — exercise definitions (name, muscle_group)
- `workouts` — workout sessions (user_id, date, notes)
- `workout_sets` — individual sets (workout_id, exercise_id, set_number, reps, weight)

Features:
- [ ] Create database migration (exercises, workouts, workout_sets with RLS)
- [ ] Build workout logging API endpoints
- [ ] Build workout logging UI in WorkoutsScreen
- [ ] Exercise selection (search/add exercises)
- [ ] Log sets with reps/weight

---

## Progress Tracking (Main App Phase 4)

- [ ] Historical workout view
- [ ] Exercise-specific progress charts
- [ ] Personal records (PR) tracking
- [ ] Volume over time visualization

---

## AI Insights (Main App Phase 5)

- [ ] Trend analysis and recommendations
- [ ] Training recommendations
- [ ] Recovery insights
- [ ] Consistency scoring

---

## Polish (Main App Phase 6)

- [ ] Flame visualization based on consistency
- [ ] Streak tracking
- [ ] Mobile-responsive improvements
- [ ] Error handling & edge cases

---

## Deployment

| Service  | Platform          | Notes                         |
|----------|-------------------|-------------------------------|
| Frontend | Vercel            | Auto-deploy from main branch  |
| Backend  | Railway or Render | Python FastAPI                |
| Database | Supabase          | PostgreSQL + Auth + Storage   |
