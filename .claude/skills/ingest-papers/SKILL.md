---
name: ingest-papers
description: "Corpus expansion workflow for the RAG chatbot — find, verify, ingest, and quality-check research papers from PMC. Use this skill when the user wants to add papers to the RAG corpus, expand a category, find papers on a topic, or mentions FUTURE-PLANS.md priorities. Also trigger when the user says things like 'add more papers', 'find papers about X', 'expand the corpus', 'ingest papers', or references priority categories (strength, recovery, body composition, etc.)."
user_invocable: true
---

# Ingest Papers — RAG Corpus Expansion

This skill walks through the full pipeline for finding research papers on PMC, ingesting them into the RAG vector database, and verifying quality. The workflow has natural pause points where the user needs to act (approving papers, downloading PDFs).

**License policy**: target CC-BY by default (keeps the corpus commercial-ready). Non-CC-BY Creative Commons papers (CC-BY-NC, CC-BY-NC-ND, etc.) MAY be ingested opportunistically when (a) the paper is high-value and (b) no CC-BY equivalent exists. The `license` column on `papers` must be populated with the exact CC variant — commercial-mode queries can then filter via `WHERE license IN ('CC0', 'CC-BY', 'CC-BY-SA', 'CC-BY-ND')`. Schema accepts: CC0, CC-BY, CC-BY-SA, CC-BY-ND, CC-BY-NC, CC-BY-NC-SA, CC-BY-NC-ND, other, unknown.

## Overview

The corpus lives in `apps/api/papers/` with metadata in `manifest.json`. Papers are ingested via `ingest_batch.py` which calls `ingest_paper()` — extracting sections with Docling+pymupdf, chunking, embedding via Voyage AI, and storing in Supabase pgvector. SHA-256 content hash dedup means re-running is always safe.

## Valid Categories

From `apps/api/src/schema/rag.py`:
```
"hypertrophy", "strength", "nutrition", "endurance",
"recovery", "mobility", "programming", "body-composition",
"general", "injury", "cardiovascular"
```

## Valid Study Types

Must be **lowercase** (Pydantic literal validation will reject uppercase):
```
"meta-analysis", "systematic-review", "rct", "review",
"observational", "case-study", "other"
```

## Workflow

### Step 1: Identify Topics

Check what the user wants to expand. If they reference priorities, read `context/FUTURE-PLANS.md` for the corpus expansion targets. Note which categories are weak and what topics are listed.

Think about additional sub-topics the user might not have listed — common gym-goer questions that the chatbot should be able to answer in this category.

### Step 2: Search PMC for Papers

Use `WebSearch` to find papers on PMC. Run multiple searches in parallel across different topics.

Primary search pattern (CC-BY target):
```
PMC "<topic keyword>" resistance training review CC-BY site:pmc.ncbi.nlm.nih.gov
```

Prefer reviews, systematic reviews, and meta-analyses — they provide the most comprehensive coverage per paper. RCTs are fine if they fill a specific gap.

**Prefer recent papers** (2019+). Exercise science evolves quickly — newer meta-analyses supersede older ones and incorporate larger sample sizes. If two papers cover the same topic, pick the more recent one. Older papers (pre-2018) are acceptable only if they're seminal works with no modern replacement.

Aim for 6-15 papers per expansion batch depending on how many papers you see fit. Too many at once makes quality verification tedious.

Before proceeding, cross-reference candidates against `apps/api/papers/manifest.json` to avoid suggesting papers already in the corpus. Check by DOI or title.

#### Author/Institution Quality Heuristic (soft preference, tiebreaker only)

When two candidate papers cover similar ground, prefer the one from a researcher/group with established reputation in that sub-domain. This is a **tiebreaker, not a filter** — a strong paper from an unknown group still gets included.

Trusted contemporary researchers by sub-domain (non-exhaustive):

- **Hypertrophy / RT**: Brad Schoenfeld (CUNY Lehman), James Krieger, Stuart Phillips (McMaster), Michael Roberts / Daniel Plotkin (Auburn), Eric Helms (AUT), Andrew Vigotsky
- **Strength / power / plyometrics**: G. Gregory Haff (Edith Cowan), Robert Newton (ECU), Rodrigo Ramirez-Campillo, Greg Nuckols / Eric Trexler (MASS)
- **Nutrition**: Stuart Phillips, Bill Campbell (USF), Eric Helms. ⚠️ Jose Antonio (ISSN) is prolific but ISSN has industry funding — fine to include with awareness.
- **Endurance**: Stephen Seiler, Iñigo San Millán
- **Recovery**: Shona Halson (ACU)
- **Mobility / flexibility**: David Behm (Memorial Newfoundland)
- **Aging / sarcopenia**: Stuart Phillips, Roger Fielding

Top institutions (treat as a positive signal): McMaster, CUNY Lehman, Auburn, AUT NZ, Edith Cowan, ACU, Liverpool John Moores.

**Quality red flags** (these aren't auto-rejections, but warrant scrutiny):
- Single-author papers in low-impact journals
- Industry-funded supplement studies with no conflict disclosure
- N<10 RCTs presenting as definitive
- Hypertrophy/strength papers placed in off-topic outlets (e.g., a training study in *IJERPH* rather than *Sports Medicine* or *JSCR*)
- Very recent (last ~12 months) primary studies with no citation history — usually better to wait for the meta-analysis that will integrate them

These are heuristics, not gates. Domain-appropriate journals matter more than author names for unfamiliar topics, and a no-name group can produce excellent work — especially in less-studied sub-domains where the "top" researchers haven't published.

#### Journal Quality Tiers (stronger signal than author heuristic — use this first)

Journals carry more reliable quality signal than first-author names for our corpus, because most "trusted" authors appear as senior (last) authors and aren't visible from PMC search results without opening the paper. Journal tier is visible at a glance.

**Tier 1 — Gold standard** (mostly paywalled, rare in PMC OA): *Medicine & Science in Sports & Exercise*, *Journal of Applied Physiology*, *Journal of Strength and Conditioning Research*, *International Journal of Sports Physiology and Performance*, *British Journal of Sports Medicine*, *American Journal of Sports Medicine*. Always accept on the rare occasion one is CC-BY in PMC.

**Tier 2 — High quality, CC-BY available in PMC OA** (the sweet spot — prefer these): *Sports Medicine* (Springer), *Sports Medicine - Open*, *European Journal of Applied Physiology* (when CC-BY, not CC-BY-NC-ND), *BMC Sports Science, Medicine and Rehabilitation*, *Translational Sports Medicine*, *BMJ Open Sport & Exercise Medicine*, *Journal of Cachexia, Sarcopenia and Muscle*.

**Tier 3 — Solid open-access workhorses** (always acceptable, the bulk of any OA corpus): *Frontiers in Physiology*, *Frontiers in Nutrition*, *Frontiers in Sports and Active Living*, *PeerJ*, *PLOS One*, *Journal of the International Society of Sports Nutrition* (⚠️ industry-tied — read funding disclosures on supplement papers), *Nutrition Reviews*.

**Tier 4 — MDPI (variable quality — scrutinize per-paper)**: *Nutrients*, *Sports*, *Journal of Functional Morphology and Kinesiology*, *Healthcare*, *Journal of Clinical Medicine*, *Life*, *Cells*, *Biology*. Acceptable when the paper itself is rigorous (proper methodology, recent meta-analysis, sensible journal-topic fit) but check more carefully than Tier 1-3.

**Tier 5 — Red flags (default-avoid)**:
- ***International Journal of Environmental Research and Public Health*** (IJERPH) — delisted from Clarivate's Journal Citation Reports in 2023 over citation gaming. Avoid for new ingestion unless no alternative exists on the topic.
- ***Cureus*** — low-bar peer review reputation; broad scope. Sanity-check methodology before accepting.

**Specialty journals not in tiers above** (mostly fine for their niche): *European Heart Journal* (cardiology), *JAMA Network Open*, *Calcified Tissue International* (bone), *Bone Reports*, *Sleep & Breathing*, *Scientific Reports*, *Journal of Cachexia, Sarcopenia and Muscle* (aging). Accept on a per-paper basis when the topic fits.

**Journal-topic fit also matters**: a hypertrophy meta-analysis in *Sports Medicine* is more credible than the same paper in a broad-scope outlet like *IJERPH* or *Healthcare*. Treat off-topic placement as a yellow flag even in Tier 4.

### Step 3: Verify and Record Licenses

For each candidate paper, fetch the PMC page with `WebFetch` and capture:
- **Exact CC license string** — CC-BY, CC-BY-SA, CC-BY-ND, CC-BY-NC, CC-BY-NC-SA, CC-BY-NC-ND, CC0. Read it off the PMC copyright/license block; do not infer from the journal.
- Exact title, authors (last name et al.), year, journal, DOI, PMC URL

Run these in parallel (6+ at a time is fine).

**Acceptance rules:**
- **CC-BY (and CC0, CC-BY-SA, CC-BY-ND)**: always accept if the paper is otherwise a good fit. These are the commercial-safe defaults.
- **CC-BY-NC variants (CC-BY-NC, CC-BY-NC-SA, CC-BY-NC-ND)**: accept opportunistically when the paper is high-value AND no recent CC-BY equivalent exists on the topic. Flag these explicitly in the curated list (Step 4) so the user can confirm. Mark them as non-commercial in the manifest.
- **Anything else** (custom license, all-rights-reserved, no machine-readable license): reject.

When considering a non-CC-BY paper, briefly note in the curated list *why* it's worth ingesting despite the license (e.g., "only recent meta-analysis on this sub-topic" or "seminal paper, no CC-BY replacement").

### Step 4: Present Curated List

Show the user a table with all verified papers. Include the License column so non-CC-BY entries are obvious at a glance:

| # | Category | Authors | Year | Title | Journal | License | PMC URL |
|---|----------|---------|------|-------|---------|---------|---------|

If any paper has a non-CC-BY license, add a short note below the table explaining why it's worth including despite the license (per Step 3 acceptance rules) so the user can confirm.

Then provide the PMC URLs as a simple numbered list so the user can click through and download the PDFs.

**PAUSE here** — wait for the user to approve the list and download the PDFs.

### Step 5: Confirm PDFs Downloaded

Once the user says they've downloaded the PDFs, verify all files exist:

```bash
ls apps/api/papers/*.pdf
```

Match each expected paper to a filename. PMC downloads typically use patterns like:
- `fphys-13-926972.pdf` (Frontiers)
- `40279_2021_Article_1587.pdf` (Springer)
- `nutrients-16-03247.pdf` (MDPI)
- `peerj-10-14142.pdf` (PeerJ)
- `sports-08-00125.pdf` (MDPI Sports)

Present the mapping to the user for confirmation before proceeding.

### Step 6: Update manifest.json

Read the current `apps/api/papers/manifest.json` and append the new entries. Match the existing format exactly:

```json
{
    "filename": "example.pdf",
    "title": "Full Paper Title",
    "authors": "Smith et al.",
    "year": 2023,
    "category": "strength",
    "license": "CC-BY",
    "journal": "Sports Medicine",
    "study_type": "meta-analysis",
    "doi": "10.1234/example",
    "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/"
}
```

**Critical:** `study_type` must be lowercase (`"rct"` not `"RCT"`). Pydantic validation will reject uppercase.

**Critical:** `license` must be the exact CC variant captured in Step 3 — one of `CC-BY`, `CC-BY-SA`, `CC-BY-ND`, `CC-BY-NC`, `CC-BY-NC-SA`, `CC-BY-NC-ND`, `CC0`. Do not default every paper to `CC-BY` without verifying. The commercial-mode query filter depends on this being accurate.

### Step 7: Run Ingestion

```bash
cd apps/api && source venv/bin/activate && python -m scripts.ingest_batch
```

This processes all papers in the manifest. Existing papers are skipped via SHA-256 dedup ("Paper already ingested"). Only new papers go through the full extract-chunk-embed-store pipeline.

Set timeout to 600000ms (10 min) — ingestion with Docling ML models takes time.

Check the output for:
- `Results: N ingested, 0 skipped, 0 failed` — all should succeed
- If any fail, check the error (usually `study_type` casing or missing PDF)

### Step 8: Verify Ingestion Quality

Query Supabase for each new paper's chunks. For each paper, check:

1. **Sections are clean** — no body text bleeding into section names, no duplicated headers, no garbled text
2. **Text is readable** — no excessive non-ASCII characters (note: `\xa0` non-breaking spaces from Springer PDFs are normal and harmless)
3. **Section count is reasonable** — most papers should have 5-15 sections

Capture the paper IDs from the ingestion output (each new paper prints `ID: <uuid>`). Then run this from `apps/api/` with venv activated:

```python
from src.db import get_supabase
sb = get_supabase()

paper_ids = ['<id1>', '<id2>', ...]  # from ingestion output

for pid in paper_ids:
    paper = sb.table('papers').select('title,authors').eq('id', pid).execute().data[0]
    chunks = sb.table('chunks').select('id,chunk_index,section,text,token_count') \
        .eq('paper_id', pid).order('chunk_index').execute().data

    sections = list(dict.fromkeys(c['section'] for c in chunks if c['section']))
    print(f'=== {paper["authors"]} — {len(chunks)} chunks ===')
    print(f'Sections: {sections}')

    # Check for garbled text
    for c in chunks:
        non_ascii = sum(1 for ch in c['text'] if ord(ch) > 127)
        if non_ascii > len(c['text']) * 0.05:
            print(f'  WARNING: chunk {c["chunk_index"]} may have garbled text')
            print(f'    Preview: {repr(c["text"][:150])}')
    print()
```

4. **No missing sections** — After running the quality check script above, review the detected sections for each paper against what a typical research paper of that study type should have:

   - **Meta-analyses / systematic reviews**: Abstract, Introduction, Methods, Results, Discussion, Conclusions, References
   - **RCTs**: Abstract, Introduction, Methods/Materials, Results, Discussion, Conclusions, References
   - **Narrative reviews**: Abstract, Introduction, [topic-specific content sections], Discussion/Conclusions, References (no Methods/Results expected)

   **For any paper where key sections appear to be missing** (e.g., a meta-analysis with no Results section, or a paper with only 2-3 detected sections), use the `Read` tool to open the actual PDF and compare the real section headings against what the pipeline detected. This catches cases where the pipeline failed to detect headers — the content is still there but assigned to the wrong section. Specifically:

   a. Read the PDF with `Read` tool (it handles PDFs natively)
   b. List the actual major section headings visible in the PDF
   c. Compare against the detected sections from the quality script
   d. If sections were missed, note the paper ID, the missing sections, and which section the content ended up under — then fix in Step 9

   **Known acceptable exceptions** (do NOT flag these as problems):
   - Frontiers papers often missing "Abstract" — content is in the first chunk under a different name or no section header
   - Short narrative reviews (< 20 chunks) having fewer sections (e.g., Background → Findings → Conclusions) is normal
   - Review papers organized by topic instead of standard IMRAD structure (Introduction, Methods, Results, Discussion)

Common issues to look for:
- **Body text in section names**: `"mance [15,46,59]. 5. Effects of Volume"` — text from previous section bled into header
- **Duplicated headers**: `"9. Topic Name 9. Topic Name"` — Docling detected the header twice
- **Author name as section**: `"John Smith"` — MDPI papers sometimes detect author names as headers
- **Back-matter bleed**: Reference chunks appearing under FUNDING or Publisher's Note sections (Frontiers papers)
- **Missing sections**: Paper has only 2-3 sections when the PDF clearly has more — header detection failed. Read the PDF to verify and compare against detected sections

### Step 9: Fix Section Issues

For **small fixes** (a few garbled section names, a duplicated header), fix them directly in Supabase:

```python
sb.table('chunks').update({'section': 'Corrected Section Name'}) \
    .eq('paper_id', '<paper_id>') \
    .eq('section', 'garbled section name here') \
    .execute()
```

For **larger issues** (missing sections, chunks assigned to wrong sections, major header detection failures), don't try to fix it manually — just report the problems to the user with details on what's wrong and which papers are affected. These may need an ingestion pipeline fix or a re-ingest with different parameters.

### Step 10: Update reingest_all.py

Read `apps/api/scripts/reingest_all.py` and append the new paper entries to the `PAPERS` list. Follow the existing format with comments grouping papers by category:

```python
# --- N new <category> papers (corpus expansion) ---
{
    "filename": "example.pdf",
    "title": "...",
    ...
},
```

Update the comment at the top of the PAPERS list to reflect the new total count.

### Step 11: Add Eval Questions

Add evaluation test cases to `apps/api/tests/eval/test_dataset.json` for the newly ingested papers. Follow the existing format:

```json
{
    "id": "CAT-NNN",
    "question": "A question a gym-goer would ask about this topic",
    "category": "category-name",
    "expected_facts": [
        "Key fact 1 the answer should contain",
        "Key fact 2 the answer should contain",
        "Key fact 3 the answer should contain"
    ],
    "expected_papers": ["Author Year", "Author Year"],
    "difficulty": "easy|medium|hard",
    "tags": ["category", "topic", "multi-paper"]
}
```

Guidelines:
- Use the category abbreviation as the ID prefix (e.g., `INJ-001`, `REC-009`, `NUT-014`)
- Aim for ~4-8 questions per expansion batch (1 per paper roughly, some multi-paper)
- Mix difficulties: a few easy (single-paper, straightforward), mostly medium, 1-2 hard (multi-paper synthesis or nuanced)
- Set `"category"` to the paper's category (enables category-filtered eval) or `null` (tests unfiltered retrieval)
- `expected_papers` should list papers that should be retrieved — use "Author Year" format matching the manifest's `authors` field
- `expected_facts` should be 3 key claims the answer must contain, grounded in the papers' actual findings
- `tags` should include the category and specific topic keywords


### Step 12: Update Context Docs

**`context/CONTEXT.md`** — Update the corpus status section:
- Update paper and chunk counts in the "Current" header
- Update the category table
- Add an expansion table showing the new papers with authors, year, topic, and chunk counts
- Update the "Test Dataset" line with new total case count and per-category breakdown

**`context/FUTURE-PLANS.md`** — Mark completed priorities or note progress:
- Add checkmark and completion details for fully completed priorities
- Update partially completed priorities with what's been added

### Step 13: Summary

Report to the user:
- How many papers ingested, how many chunks
- Any quality issues found and fixed
- Updated corpus totals by category
- What eval questions should be added next (if applicable)
