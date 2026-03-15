# Future Plans & Improvement Ideas

---

## RAG v1 Improvements (before moving to v2)

### Abstract-Augmented Retrieval
After normal top-k retrieval, check which papers the returned chunks come from. For each cited paper, if its abstract chunk isn't already in the top-k, inject it into the prompt context. Gives the LLM both the forest (abstract = paper's overall conclusion) and the trees (specific chunks = evidence). Cheap — abstracts are already stored as chunks, just lookup by paper_id + section="Abstract".

### Re-ranking
Add a cross-encoder to re-rank top-k results. Current retrieval relies solely on pgvector cosine similarity (bi-encoder). A cross-encoder scores each (query, chunk) pair more accurately but is slower — so use it as a second pass on the top-20 → pick best 5. Improves precision, especially as corpus grows and more chunks compete for top-k slots.

### Increase top_k
Currently top_k=5. As corpus grows past ~100 papers (~4000 chunks), consider bumping to 8-10 to reduce the chance of missing relevant chunks. Trade-off: more context tokens used, slightly higher cost. Monitor retrieval quality via eval scores.

### Two-Stage Retrieval
Search abstracts first to identify relevant papers, then search chunks within those papers for specific evidence. Better for broad questions that span multiple papers. More of an architectural change — defer until v1 improvements plateau.

### Cross-Validate Eval with Different Judge Model
Current eval uses same model (Gemini 2.5 Flash) as both RAG generator and judge — same-model bias may inflate faithfulness scores. Use `--judge-model` flag to cross-validate with GPT-4o or Claude. Already supported in CLI.

### Async Supabase in Web Handlers
`supabase-py` is synchronous. DB calls in SSE handler block briefly but nothing else is waiting. For production, wrap in `asyncio.to_thread()` to avoid blocking the event loop.

---

## RAG v2: Agentic RAG with Router

### Architecture
```
User question
      |
      v
   Router (LLM classifies intent)
      |
      +-- "literature question"  --> RAG Pipeline (v1)
      |
      +-- "workout data question" --> SQL query against workout tables
      |                              (workouts, exercises, workout_sets)
      |
      +-- "both" --> Run both, combine
                     ("Research says 10-20 sets/week. You're doing 14.")
```

### Why a Router
Literature = unstructured text -> vector search. Workout data = structured numbers -> SQL queries. Fundamentally different retrieval methods require a routing decision.

### Prerequisites
- Workout logging feature must be built first (Phase 3 in PLAN.md)
- v1 RAG must be stable with good eval scores
- Need sufficient workout data in the DB to test against

---

## Corpus Expansion Targets

All papers should be CC-BY from PMC Open Access Subset (`cc by license[filter]`).

### Priority 1: Strength (currently only 5 papers)
- Progressive overload principles
- Specificity and transfer of training
- Velocity-based training / autoregulation (RPE/RIR)
- Concurrent training (does cardio kill strength gains? — interference effect)

### Priority 2: Recovery & Fatigue Management (no training-side papers)
- Overtraining / overreaching / functional overreaching
- Deloading strategies (when, how much, how long)
- Active recovery methods
- Sleep and exercise performance (beyond nutrition-sleep)

### Priority 3: Body Composition (common gym user questions)
- Body recomposition (muscle gain + fat loss simultaneously)
- Cardio + resistance training interaction (interference effect)
- Fat loss strategies that preserve muscle

### Priority 4: Flexibility / Warm-up (completely absent)
- Stretching before/after lifting (acute effects on performance)
- Foam rolling / self-myofascial release
- Warm-up protocols for resistance training

### Priority 5: Training for Specific Populations
- Older adults / sarcopenia / age-related muscle loss
- Sex differences in hypertrophy/strength responses
- Beginners vs advanced (training age differences)

### After Each Expansion
- Update `reingest_all.py` and `manifest.json`
- Add corresponding eval questions to `test_dataset.json`
- Re-run eval and compare to previous baseline

---

## App Features (PLAN.md Phases 3-6)

### Phase 3: Workout Logging (next)
- Database schema: `exercises`, `workouts`, `workout_sets` tables
- API endpoints for CRUD
- UI in WorkoutsScreen: exercise selection, set/rep/weight logging

### Phase 4: Progress Tracking
- Historical workout view
- Exercise-specific progress charts
- Personal records (PRs) tracking
- Volume over time visualization

### Phase 5: AI Insights
- Trend analysis using workout data
- Training recommendations
- Recovery insights
- Consistency scoring

### Phase 6: Polish
- Flame visualization based on consistency
- Streak tracking
- Mobile-responsive improvements
- Error handling & edge cases

---

## Deployment
| Service | Platform |
|---------|----------|
| Frontend | Vercel (auto-deploy from main) |
| Backend | Railway or Render |
| Database | Supabase (already running) |
