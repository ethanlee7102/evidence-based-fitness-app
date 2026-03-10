# Docling Refactor — Implementation Context

## Problem

Double-column PDFs have section content assigned to wrong headers because pymupdf's `sort=True` breaks reading order when headers and content are in different columns. Affected: Latella 2020 (JSCR) and Androulakis-Korakakis 2021 (Frontiers).

## Decision: IBM Docling + pymupdf hybrid

- **Docling** (DocLayNet ML model) handles reading order, header detection, column layouts, tables, header/footer exclusion
- **pymupdf** used only for font size lookups on Docling-detected headers (to classify major vs minor)
- Docling's ML model detects headers accurately but has no hierarchy — all headers are level 1. Font sizes from pymupdf restore hierarchy.

### Options evaluated and rejected
1. `pymupdf4llm` — markdown-based, still font analysis under the hood
2. `Marker`, `MinerU` — other ML approaches, less mature
3. Manual `column_boxes()` — heuristic on top of heuristics
4. Docling heading level (`item.level`) — always 1 for all papers tested
5. Docling tree depth (`iterate_items()` depth) — always 1, flat structure
6. Docling markdown export — all `##`, no hierarchy

---

## Final Implementation (`apps/api/src/core/ingestion.py`)

**Dependencies**: `docling>=2.0.0` + `pymupdf>=1.24.0` + `langchain-text-splitters>=0.2.0`

**Architecture**: Multi-pass extraction in `extract_sections()`:
1. **Pass 1 (Docling)**: `DocumentConverter.convert()` → `doc.iterate_items()` in correct reading order. Classifies items by `DocItemLabel` (SECTION_HEADER, TABLE, PICTURE, TEXT, etc.). Tables exported as markdown. Pictures skipped. Page numbers 1-based from `item.prov[0].page_no`. Stores header bboxes for Pass 2.
2. **Pass 2 (pymupdf font size)**: `_classify_major_headers()` determines which Docling headers are major section breaks vs subsections via bounding box spatial matching.
3. **Abstract detection**: Force-promotes "Abstract" headers to major. Scans pre-header body text for "Abstract:" labels and injects synthetic section breaks.

**Lazy converter singleton**: `_get_converter()` loads Docling ML models once (~6.2 GB download on first run to `~/.cache/huggingface/hub/`), reuses for batch ingestion.

**Header hierarchy classification** (`_classify_major_headers()`):
- **Layer 1a (font size grouping)**: `_find_font_info_by_bbox()` converts Docling bbox (BOTTOMLEFT) to pymupdf coords (TOPLEFT), finds overlapping spans, reads font size and bold flag. `_group_by_font_size()` clusters by size with 0.5pt tolerance. Picks the largest font group with >= 2 members.
- **Layer 1b (bold tiebreaker)**: If selected font-size group has bold/non-bold mix, only bold = major (handles MDPI journals).
- **Layer 1c (ALL_CAPS tiebreaker)**: If selected font-size group has CAPS/mixed-case mix AND group is >70% of valid headers, only CAPS = major (handles Frontiers journals). Gated to avoid demoting legitimate majors in well-split papers.
- **Layer 2 (ALL_CAPS / numbered)**: Fallback when font sizes are uniform.
- **Layer 3**: Final fallback — all headers kept as section breaks.

**Abstract detection** (after hierarchy classification):
- Force-promotes any Docling header matching `^abstract\b` (case-insensitive) to major regardless of font size
- Scans body text before first major header for "Abstract:" prefix (regex: `^abstract\s*[:\-—.]?\s*`). Injects synthetic "Abstract" header + remaining text as body. Handles MDPI papers where abstract is body text.
- Result: 7/9 papers have Abstract as own section. 2 Frontiers papers have unlabeled abstracts.

**Key functions**: `_bbox_overlap()`, `_find_font_info_by_bbox()`, `_group_by_font_size()`, `_is_all_caps()`, `_classify_major_headers()`

**Unchanged functions**: `compute_content_hash()`, `_find_page_range()`, `chunk_sections()`, `ingest_paper()` — same interfaces.

### Final test results (after re-ingestion)

**9 papers, 414 total chunks**:
```
nutrients-13 — 70 chunks, 9 sections incl. Abstract (body text scan, bold tiebreaker)
nutrients-17 — 71 chunks, 7 sections incl. Abstract (Docling header + force-promote)
ijerph-16   — 28 chunks, 7 sections incl. Abstract (body text scan, bold tiebreaker)
fspor-04    — 32 chunks, 9 sections (ALL_CAPS tiebreaker, no abstract label in PDF)
sports-09   — 52 chunks, 8 sections incl. Abstract (body text scan)
sports-08   — 34 chunks, 8 sections incl. Abstract (body text scan, bold tiebreaker)
fspor-03    — 64 chunks, 16 sections (font size grouping, no abstract label in PDF)
jscr-34     — 20 chunks, 10 sections incl. Abstract (Docling header + force-promote)
40279_2019  — 43 chunks, 8 sections incl. Abstract (Docling header + force-promote)
```

Retrieval verified with cross-paper queries (similarity 0.65-0.75).

---

## Resolved Issues

All three issues from the font-map approach were resolved by switching to **bounding box matching**.

### Root cause (font map approach)
`_build_font_size_map()` built a text→font-size lookup from pymupdf blocks, then `_lookup_header_font_size()` tried to match Docling headers against it by text. This failed because pymupdf fragments text differently than Docling — many legitimate headers got `None` and were silently excluded from hierarchy classification.

### Fix: Bounding box spatial matching + tiebreakers
Instead of matching by text, match by position. Docling provides `item.prov[0].bbox` for each header. pymupdf provides `span["bbox"]` for each text span. The coordinate systems differ only by a y-axis flip:
- **x**: identical between Docling and pymupdf
- **y**: `pymupdf_y = page_height - docling_y` (Docling uses BOTTOMLEFT origin, pymupdf uses TOPLEFT)
- Discrepancies consistently < 1pt, handled with 2pt overlap tolerance

**Bold tiebreaker** (Layer 1b): pymupdf's `span["flags"]` bit 4 indicates bold. When font size grouping selects a major group where all headers are the same size, if there's a bold/non-bold mix, bold headers are kept as major and non-bold are demoted. Handles MDPI-format papers (URWPalladioL font family) where top-level headers are bold and subsections are italic, both at the same font size.

**ALL_CAPS tiebreaker** (Layer 1c): When the font-size group has ALL_CAPS/mixed-case mix AND the group represents >70% of all valid headers, only ALL_CAPS = major. The >70% gate prevents over-splitting in papers where font size already made a meaningful split (e.g., fspor-03 where 12pt correctly separates Study headers).

**Abstract detection**: Force-promotes "Abstract" headers to major regardless of font size. Also scans body text before the first major header for "Abstract:" prefix and injects a synthetic section break. Handles MDPI papers where abstract is body text (`[text]` label), not a `[section_header]`.

**New functions**: `_bbox_overlap()`, `_find_font_info_by_bbox()`, `_is_all_caps()` — replaced `_build_font_size_map()`, `_lookup_header_font_size()`

### Results
- **246/246 headers matched (100%)** across all 9 papers — zero misses
- **Issue 1 (JSCR table captions)**: Fixed. Table captions are 8.0pt, real headers are 9.5pt. Bbox matching finds both, font grouping correctly separates them. JSCR now has 9 clean sections (was 11 with 2 false positives).
- **Issue 2 (Frontiers font map failures)**: Fixed. All headers now have font sizes via spatial lookup. Study 1-5 (12pt) correctly identified as major, subsections (10pt) demoted. Frontiers now has 16 sections with proper hierarchy (was 12 with Studies swallowed).
- **Issue 3 (Supplementary Material . false positive)**: Fixed. "Supplementary Material ." is 9.5pt in the Frontiers paper — below the 12pt major header threshold. No longer creates a false section break.

---

## Files Changed

| File | Status | Change |
|------|--------|--------|
| `apps/api/requirements.txt` | Done | Added `docling>=2.0.0`, kept `pymupdf>=1.24.0` |
| `apps/api/src/core/ingestion.py` | Done | Rewrote `extract_sections()`, added `_get_converter()`, `_bbox_overlap()`, `_find_font_info_by_bbox()`, `_group_by_font_size()`, `_is_all_caps()`, `_classify_major_headers()`, abstract detection |
| `apps/api/scripts/reingest_all.py` | Done | New script: delete all papers/chunks + re-ingest all 9 papers |
| `CLAUDE.md` | Done | Updated ingestion description, pipeline step 1, tech stack |
| `CONTEXT.md` | Done | Updated Phase 3 section detection, Phase 2 deps, double-column issue section |
| `MEMORY.md` | Done | Updated Phase 2 deps, Phase 3 section detection |

**Unchanged**: `chunk_sections()`, `_find_page_range()`, `ingest_paper()`, scripts, retrieval, schemas, app.py

---

## Docling API Reference (confirmed from source)

```python
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.labels import DocItemLabel

# Convert
converter = DocumentConverter(format_options={...})
result = converter.convert(pdf_path)
doc = result.document

# Iterate (correct reading order, excludes headers/footers)
for item, level in doc.iterate_items():
    item.label      # DocItemLabel enum (SECTION_HEADER, TABLE, TEXT, PICTURE, etc.)
    item.text       # str (all items except TABLE)
    item.level      # int (heading depth, but always 1 in practice)
    item.prov       # list[ProvenanceItem] — prov[0].page_no (1-based), prov[0].bbox
    # For tables:
    item.export_to_markdown(doc)  # must pass doc as argument

# Bounding box coordinate system
item.prov[0].bbox  # BoundingBox(l, t, r, b, coord_origin=BOTTOMLEFT)
# Convert to pymupdf TOPLEFT: y_pymupdf = page_height - y_docling

# Export full document
doc.export_to_markdown()  # all ## headers (no hierarchy)
```

- `DocItemLabel` is a string enum: `SECTION_HEADER == "section_header"`, `TABLE == "table"`, etc.
- `item.level` is always 1 for all papers tested (no hierarchy info)
- `iterate_items()` second value is tree traversal depth (also always 1)
- First run downloads ~6.2 GB of ML models to `~/.cache/huggingface/hub/`

---

## Font Size Data from Test Papers (via bbox matching)

### JSCR (Latella 2020)
| Size | Headers |
|------|---------|
| 19.9pt | Title |
| 10.0pt | Author line |
| 9.5pt | Introduction, Methods, Results, Discussion, Practical Applications, Acknowledgments, References |
| 9.0pt | Abstract, Experimental Approach, Subjects, Procedures, Statistical Analyses, subsections |
| 8.0pt | Table 1, Table 2, table captions |

9.5pt group = major headers. Table captions (8.0pt) correctly separated.

### Frontiers (Androulakis-Korakakis 2021)
| Size | Headers |
|------|---------|
| 20.9pt | Title |
| 12.0pt | INTRODUCTION, OVERVIEW OF STUDIES, Study 1..., Study 2..., Studies 3 and 4..., Study 5..., General Discussion, CONCLUSIONS, REFERENCES, etc. |
| 10.0pt | Participants, Procedures, Discussion, Results, PL Athletes, PL Coaches, etc. |
| 9.5pt | Supplementary Material . |
| 7.0pt | Edited by:, Reviewed by:, *Correspondence:, etc. |

12.0pt group = major headers. All Study headers now correctly found at 12pt.
