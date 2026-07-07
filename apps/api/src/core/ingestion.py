"""Paper ingestion pipeline.

Takes PDF research papers, extracts text with section awareness,
chunks them, embeds via Voyage AI, and stores in Supabase.

Uses IBM Docling for PDF parsing — ML-based layout analysis (DocLayNet model)
handles double-column layouts, section headers, and tables automatically.
Header hierarchy is determined by a layered approach:
  1a. Bounding box matching: Docling header bbox → pymupdf span → font size grouping
  1b. Bold tiebreaker: within a same-size group, bold = major, non-bold = minor
  1c. ALL_CAPS tiebreaker: within a same-size group, ALL_CAPS = major, mixed-case = minor
  2. ALL_CAPS / numbered prefix fallback (when font sizes are uniform)

Note: uses sync Supabase client inside async functions. Fine for CLI scripts.
Wrap DB calls in asyncio.to_thread() if ever called from web request handlers.
"""

import hashlib
import logging
import re

import fitz  # pymupdf — used only for font size lookups on Docling-detected headers
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.labels import DocItemLabel
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.embedding_provider import embed_texts
from src.core.noise_filter import is_noise
from src.db import get_supabase
from src.schema.rag import PaperMetadata, PaperResponse
from src.utils.config import config

logger = logging.getLogger(__name__)

# Lazy singleton — loads ML models once on first use, reuses for batch ingestion
_converter: DocumentConverter | None = None

# Font size tolerance for grouping (sizes within this range are considered the same)
_FONT_SIZE_TOLERANCE = 0.5

# Bounding box overlap tolerance in points (handles sub-point coord rounding)
_BBOX_TOLERANCE = 2.0


def _get_converter() -> DocumentConverter:
    """Get or create the Docling document converter (lazy singleton)."""
    global _converter
    if _converter is None:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.generate_picture_images = False
        pipeline_options.generate_page_images = False
        _converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
    return _converter


def _bbox_overlap(a: tuple, b: tuple, tolerance: float = _BBOX_TOLERANCE) -> bool:
    """Check if two (x0, y0, x1, y1) rects overlap, with tolerance in points."""
    return not (
        a[0] > b[2] + tolerance
        or a[2] < b[0] - tolerance
        or a[1] > b[3] + tolerance
        or a[3] < b[1] - tolerance
    )


def _find_font_info_by_bbox(
    pymupdf_page, docling_bbox, page_height: float,
) -> tuple[float | None, bool]:
    """Find a Docling header's font size and bold status by spatial lookup.

    Converts Docling's BOTTOMLEFT bbox to pymupdf's TOPLEFT coordinates,
    then finds overlapping spans. Returns (max_font_size, is_bold) where
    is_bold comes from the largest overlapping span.

    pymupdf span flags: bit 4 = bold.
    """
    target = (
        docling_bbox.l,
        page_height - docling_bbox.t,
        docling_bbox.r,
        page_height - docling_bbox.b,
    )

    max_size: float = 0
    is_bold = False
    for block in pymupdf_page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if _bbox_overlap(target, span["bbox"]) and span["size"] > max_size:
                    max_size = span["size"]
                    is_bold = bool(span["flags"] & (1 << 4))

    return (max_size if max_size > 0 else None, is_bold)


def _group_by_font_size(
    sizes: list[float], tolerance: float = _FONT_SIZE_TOLERANCE,
) -> list[list[int]]:
    """Group indices by font size, with tolerance for rounding.

    Returns groups sorted by font size descending (largest first).
    Each group is a list of indices into the input list.
    """
    if not sizes:
        return []

    # Sort indices by font size descending
    indexed = sorted(enumerate(sizes), key=lambda x: x[1], reverse=True)

    groups: list[list[int]] = []
    current_group: list[int] = [indexed[0][0]]
    current_size = indexed[0][1]

    for idx, size in indexed[1:]:
        if current_size - size <= tolerance:
            current_group.append(idx)
        else:
            groups.append(current_group)
            current_group = [idx]
            current_size = size

    groups.append(current_group)
    return groups


def _is_all_caps(text: str) -> bool:
    """Check if text is ALL_CAPS (at least 3 alpha chars, all uppercase)."""
    alpha_chars = [c for c in text if c.isalpha()]
    return len(alpha_chars) >= 3 and all(c.isupper() for c in alpha_chars)


def _classify_major_headers(
    headers: list[tuple[str, int, object | None]],
    pdf_path: str,
) -> set[int]:
    """Classify which Docling-detected headers are major section breaks.

    Uses a layered approach:
      1a. Bounding box matching — Docling bbox → pymupdf span → font size → grouping
      1b. Bold tiebreaker — if the font-size group has a bold/non-bold mix,
          use only the bold headers as major
      1c. ALL_CAPS tiebreaker — if the font-size group has an ALL_CAPS/mixed-case mix,
          use only the ALL_CAPS headers as major
      2. Fallback (uniform font size) — ALL_CAPS or numbered prefix = major headers
      3. Final fallback — all headers are major (no hierarchy detected)

    Args:
        headers: List of (header_text, page_num, docling_bbox) for each header.
            docling_bbox may be None if provenance was missing.
        pdf_path: Path to the PDF for font size lookups.

    Returns set of indices into `headers` that are major section breaks.
    """
    if len(headers) <= 1:
        return set(range(len(headers)))

    # --- Layer 1a: Bounding box matching for font sizes and bold flags ---
    pdf_doc = fitz.open(pdf_path)
    font_sizes: list[float | None] = []
    bold_flags: list[bool] = []
    for _text, page_num, bbox in headers:
        if bbox is not None:
            page = pdf_doc[page_num - 1]
            size, bold = _find_font_info_by_bbox(page, bbox, page.rect.height)
            font_sizes.append(size)
            bold_flags.append(bold)
        else:
            font_sizes.append(None)
            bold_flags.append(False)
    pdf_doc.close()

    # Filter to headers where we found a font size
    valid = [(i, size) for i, size in enumerate(font_sizes) if size is not None]

    if valid:
        valid_indices, valid_sizes = zip(*valid)
        groups = _group_by_font_size(list(valid_sizes))

        if len(groups) >= 2:
            # Multiple font size groups — find the largest font group that represents
            # actual section headers (not just the paper title/label).
            # Heuristic: if the largest group has <= 2 members and the next qualifying
            # group has >= 3, the small top group is likely title-level — skip it.
            qualifying = [(gi, group) for gi, group in enumerate(groups) if len(group) >= 2]

            while (len(qualifying) >= 2
                    and len(qualifying[0][1]) <= 2
                    and any(len(q[1]) >= 3 for q in qualifying[1:])):
                # Skip title-level / page-label group, use the next real one
                _skipped = qualifying[0][1]
                _skipped_texts = [headers[valid_indices[i]][0][:40] for i in _skipped]
                logger.info(
                    f"Skipping title-level font group ({len(_skipped)} headers: "
                    f"{_skipped_texts}) in favor of larger group downstream"
                )
                qualifying = qualifying[1:]

            for _gi, group in qualifying:
                if len(group) >= 2:
                    major_indices = set(valid_indices[i] for i in group)

                    # --- Layer 1b: Bold tiebreaker ---
                    # If the font-size group has a mix of bold and non-bold,
                    # use only bold headers as major (common in MDPI journals)
                    bold_in_major = {i for i in major_indices if bold_flags[i]}
                    if bold_in_major and len(bold_in_major) < len(major_indices) and len(bold_in_major) >= 2:
                        logger.info(
                            f"Header hierarchy: {len(groups)} font size groups, "
                            f"bold tiebreaker {len(major_indices)} → "
                            f"{len(bold_in_major)} major headers"
                        )
                        return bold_in_major

                    # --- Layer 1c: ALL_CAPS tiebreaker ---
                    # If the font-size group has a mix of ALL_CAPS and mixed-case,
                    # use only ALL_CAPS as major (common in Frontiers journals).
                    # Only activate when font size didn't make a meaningful split
                    # (major group is >70% of all valid headers), to avoid
                    # demoting legitimate major headers in well-split papers.
                    caps_in_major = {i for i in major_indices if _is_all_caps(headers[i][0])}
                    major_is_most = len(major_indices) > 0.7 * len(valid)
                    if (caps_in_major and len(caps_in_major) < len(major_indices)
                            and len(caps_in_major) >= 2 and major_is_most):
                        logger.info(
                            f"Header hierarchy: {len(groups)} font size groups, "
                            f"ALL_CAPS tiebreaker {len(major_indices)} → "
                            f"{len(caps_in_major)} major headers"
                        )
                        return caps_in_major

                    logger.info(
                        f"Header hierarchy: {len(groups)} font size groups, "
                        f"{len(major_indices)} major headers (layer 1: bbox font size)"
                    )
                    return major_indices

    # --- Layer 2: Fallback — ALL_CAPS or numbered prefix ---
    major_indices: set[int] = set()
    for i, (text, _page, _bbox) in enumerate(headers):
        stripped = text.strip()
        is_numbered = bool(re.match(r"^\d+\.\s+\S", stripped))

        if _is_all_caps(stripped) or is_numbered:
            major_indices.add(i)

    if major_indices:
        logger.info(
            f"Header hierarchy: uniform font size, "
            f"{len(major_indices)} major headers (layer 2: caps/numbering)"
        )
        return major_indices

    # --- Layer 3: Final fallback — all headers are major ---
    logger.info("Header hierarchy: no hierarchy detected, keeping all headers")
    return set(range(len(headers)))


def compute_content_hash(pdf_path: str) -> str:
    """SHA-256 hash of raw PDF bytes for deduplication."""
    with open(pdf_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def extract_sections(pdf_path: str) -> list[dict]:
    """Extract text from PDF with section awareness and page tracking.

    Uses Docling's ML-based layout analysis (DocLayNet model) to detect
    section headers, handle double-column layouts, exclude headers/footers,
    and extract tables as markdown.

    Header hierarchy is determined by a layered approach:
      1. Bounding box matching: Docling bbox → pymupdf span → font size → grouping
      2. ALL_CAPS / numbered prefix fallback (when font sizes are uniform)
      3. Keep all headers (no hierarchy detected)

    Only major headers trigger section breaks. Minor headers (subsections)
    are folded into the body text of their parent section.

    Falls back to a single section if <= 1 major headers are detected.

    Returns list of:
        {
            "section": str | None,
            "text": str,
            "page_map": [(char_offset, page_number), ...]
        }
    where page_map tracks which page each character came from,
    enabling accurate per-chunk page numbers after splitting.
    Page numbers are 1-based.
    """
    converter = _get_converter()
    result = converter.convert(pdf_path)
    doc = result.document

    # --- Pass 1: Iterate items in reading order, collect all blocks ---
    # Store (text, page, is_header) where is_header is Docling's raw classification
    raw_blocks: list[tuple[str, int, bool]] = []
    # Bboxes for header blocks only (block_index → docling bbox)
    header_bboxes: dict[int, object] = {}

    for item, _level in doc.iterate_items():
        # Skip pictures (no text content)
        if item.label == DocItemLabel.PICTURE:
            continue

        # Determine page number (1-based, default to 1 if provenance missing)
        page_num = item.prov[0].page_no if item.prov else 1

        if item.label == DocItemLabel.SECTION_HEADER:
            idx = len(raw_blocks)
            raw_blocks.append((item.text.strip(), page_num, True))
            if item.prov:
                header_bboxes[idx] = item.prov[0].bbox
        elif item.label == DocItemLabel.TABLE:
            # Tables have no .text — export as markdown
            table_md = item.export_to_markdown(doc)
            if table_md.strip():
                raw_blocks.append((table_md.strip(), page_num, False))
        else:
            # TEXT, PARAGRAPH, LIST_ITEM, FORMULA, etc.
            text = item.text.strip() if hasattr(item, "text") else ""
            if text:
                raw_blocks.append((text, page_num, False))

    if not raw_blocks:
        return [{"section": None, "text": "", "page_map": []}]

    # --- Pass 2: Classify which headers are major section breaks ---
    # Collect all Docling-detected headers with their indices and bboxes
    header_entries: list[tuple[str, int, object | None]] = []  # (text, page_num, bbox)
    header_block_indices: list[int] = []  # index into raw_blocks
    for i, (text, page_num, is_header) in enumerate(raw_blocks):
        if is_header:
            header_entries.append((text, page_num, header_bboxes.get(i)))
            header_block_indices.append(i)

    # Determine which are major
    major_set = _classify_major_headers(header_entries, pdf_path)

    # Build the set of raw_blocks indices that are major headers
    major_block_indices = {header_block_indices[i] for i in major_set}

    # Force-promote "Abstract" to major — it's always a meaningful section break
    # even when its font size is smaller than the main headers
    for i, block_idx in enumerate(header_block_indices):
        text = raw_blocks[block_idx][0]
        if re.match(r"^abstract\b", text.strip(), re.IGNORECASE):
            major_block_indices.add(block_idx)

    # Reclassify: only major headers are treated as section breaks
    text_blocks: list[tuple[str, int, bool]] = []
    for i, (text, page_num, is_header) in enumerate(raw_blocks):
        if is_header and i in major_block_indices:
            text_blocks.append((text, page_num, True))
        else:
            # Minor headers become body text
            text_blocks.append((text, page_num, False))

    # --- Detect abstract in body text before the first major header ---
    # Some papers (MDPI, Frontiers) have "Abstract:" as body text, not a header.
    # Scan body blocks before the first major header and inject a synthetic
    # "Abstract" section break if found.
    first_major_idx = next(
        (i for i, (_, _, is_h) in enumerate(text_blocks) if is_h), len(text_blocks)
    )
    for i in range(first_major_idx):
        text, page_num, _ = text_blocks[i]
        match = re.match(r"^abstract\s*[:\-—.]?\s*", text, re.IGNORECASE)
        if match:
            remainder = text[match.end():].strip()
            # Replace block with "Abstract" header + remaining body text
            text_blocks[i] = ("Abstract", page_num, True)
            if remainder:
                text_blocks.insert(i + 1, (remainder, page_num, False))
            break  # only inject one abstract

    # --- Group blocks into sections ---
    header_count = sum(1 for _, _, is_header in text_blocks if is_header)

    if header_count <= 1:
        # Fallback: treat entire document as one section
        text_parts: list[str] = []
        page_map: list[tuple[int, int]] = []
        char_offset = 0
        for block_text, page_num, _ in text_blocks:
            page_map.append((char_offset, page_num))
            text_parts.append(block_text)
            char_offset += len(block_text) + 1  # +1 for newline

        return [{
            "section": None,
            "text": "\n".join(text_parts),
            "page_map": page_map,
        }]

    # Multiple major headers — group into sections
    sections: list[dict] = []
    current_section: str | None = None
    current_text_parts: list[str] = []
    current_page_map: list[tuple[int, int]] = []
    current_char_offset = 0

    for block_text, page_num, is_header in text_blocks:
        if is_header:
            # Save previous section if it has content
            if current_text_parts:
                sections.append({
                    "section": current_section,
                    "text": "\n".join(current_text_parts),
                    "page_map": current_page_map,
                })

            # Start new section
            current_section = block_text.strip()
            current_text_parts = []
            current_page_map = []
            current_char_offset = 0
        else:
            current_page_map.append((current_char_offset, page_num))
            current_text_parts.append(block_text)
            current_char_offset += len(block_text) + 1

    # Don't forget the last section
    if current_text_parts:
        sections.append({
            "section": current_section,
            "text": "\n".join(current_text_parts),
            "page_map": current_page_map,
        })

    return sections


def _find_page_range(
    chunk_text: str,
    section_text: str,
    page_map: list[tuple[int, int]],
) -> tuple[int | None, int | None]:
    """Find which pages a chunk spans using the section's char-offset-to-page map.

    Returns (page_start, page_end) or (None, None) if page_map is empty.
    """
    if not page_map:
        return None, None

    # Find where the chunk starts in the section text
    chunk_start = section_text.find(chunk_text)
    if chunk_start == -1:
        # Chunk may have been slightly modified by the splitter (whitespace trimming).
        # Fall back to the section's full page range.
        return page_map[0][1], page_map[-1][1]

    chunk_end = chunk_start + len(chunk_text)

    # Find page for chunk_start: last page_map entry with offset <= chunk_start
    page_start = page_map[0][1]
    for offset, page_num in page_map:
        if offset <= chunk_start:
            page_start = page_num
        else:
            break

    # Find page for chunk_end: last page_map entry with offset <= chunk_end
    page_end = page_start
    for offset, page_num in page_map:
        if offset <= chunk_end:
            page_end = page_num
        else:
            break

    return page_start, page_end


def chunk_sections(sections: list[dict]) -> list[dict]:
    """Split sections into chunks with metadata.

    Uses RecursiveCharacterTextSplitter within each section (never across
    section boundaries). Sequential chunk_index across the entire paper.

    Returns list of:
        {
            "text": str,
            "section": str | None,
            "chunk_index": int,
            "page_start": int | None,
            "page_end": int | None,
            "token_count": int,
        }
    """
    # CHUNK_SIZE is in tokens (800), convert to chars (~4 chars/token)
    char_chunk_size = config.CHUNK_SIZE * 4
    char_overlap = config.CHUNK_OVERLAP

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=char_chunk_size,
        chunk_overlap=char_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    all_chunks: list[dict] = []
    raw_index = 0    # position across ALL splits (drives the front-matter guard)
    chunk_index = 0  # sequential index over KEPT chunks only (no gaps)
    dropped = 0

    for section in sections:
        section_text = section["text"]
        if not section_text.strip():
            continue

        splits = splitter.split_text(section_text)

        for split_text in splits:
            # Drop reference-list / boilerplate chunks before they reach the
            # embedder. See src/core/noise_filter.py for the validated rule.
            # conservative=True: at ingestion there is no human reviewer, so the
            # filter must never silently drop real content — it spares any chunk
            # showing real content and errs toward keeping. See noise_filter.py.
            noise, _reason = is_noise(split_text, section["section"], raw_index, conservative=True)
            raw_index += 1
            if noise:
                dropped += 1
                continue

            page_start, page_end = _find_page_range(
                split_text, section_text, section["page_map"]
            )
            all_chunks.append({
                "text": split_text,
                "section": section["section"],
                "chunk_index": chunk_index,
                "page_start": page_start,
                "page_end": page_end,
                "token_count": int(len(split_text) / 4),
            })
            chunk_index += 1

    if dropped:
        logger.info("chunk_sections: dropped %d noise chunk(s), kept %d", dropped, len(all_chunks))

    return all_chunks


async def ingest_paper(pdf_path: str, metadata: PaperMetadata) -> PaperResponse:
    """Full ingestion pipeline: hash → dedup → extract → chunk → embed → store.

    Returns PaperResponse on success (or for already-ingested papers).
    On failure during DB insert, cleans up the paper row to prevent orphans.
    """
    supabase = get_supabase()

    # 1. Content hash for dedup
    content_hash = compute_content_hash(pdf_path)
    logger.info(f"Content hash: {content_hash[:12]}...")

    # 2. Check if already ingested
    existing = (
        supabase.table("papers")
        .select("*")
        .eq("content_hash", content_hash)
        .execute()
    )
    if existing.data:
        row = existing.data[0]
        logger.info(f"Paper already ingested: {row['title']} ({row['total_chunks']} chunks)")
        return PaperResponse(**row)

    # 3. Extract sections from PDF
    logger.info(f"Extracting sections from: {pdf_path}")
    sections = extract_sections(pdf_path)
    section_names = [s["section"] for s in sections if s["section"]]
    logger.info(f"Found {len(sections)} sections: {section_names or ['(no headers detected)']}")

    # 4. Chunk sections
    chunks = chunk_sections(sections)
    logger.info(f"Created {len(chunks)} chunks")

    if not chunks:
        raise ValueError(f"No chunks extracted from {pdf_path}")

    # 5. Embed all chunks
    logger.info(f"Embedding {len(chunks)} chunks via Voyage AI...")
    embeddings = await embed_texts([c["text"] for c in chunks])

    # 6-8. Store in DB (with cleanup on failure)
    paper_id: str | None = None
    try:
        # 6. Insert paper row
        paper_data = {
            "title": metadata.title,
            "authors": metadata.authors,
            "year": metadata.year,
            "journal": metadata.journal,
            "doi": metadata.doi,
            "url": metadata.url,
            "category": metadata.category,
            "study_type": metadata.study_type,
            "abstract": metadata.abstract,
            "license": metadata.license,
            "content_hash": content_hash,
            "total_chunks": len(chunks),
            "embedding_model": config.EMBEDDING_MODEL,
        }

        result = supabase.table("papers").insert(paper_data).execute()
        paper_id = result.data[0]["id"]
        logger.info(f"Inserted paper: {paper_id}")

        # 7. Insert chunk rows (batch insert)
        chunk_rows = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_rows.append({
                "paper_id": paper_id,
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
                "section": chunk["section"],
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
                "token_count": chunk["token_count"],
                "embedding": embedding,
            })

        supabase.table("chunks").insert(chunk_rows).execute()
        logger.info(f"Inserted {len(chunk_rows)} chunks")

    except Exception:
        # Clean up paper row to prevent orphans
        if paper_id:
            logger.error(f"Chunk insert failed, deleting paper {paper_id}")
            supabase.table("papers").delete().eq("id", paper_id).execute()
        raise

    # 8. Return response
    paper_row = (
        supabase.table("papers")
        .select("*")
        .eq("id", paper_id)
        .execute()
    )
    return PaperResponse(**paper_row.data[0])
