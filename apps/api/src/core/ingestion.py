"""Paper ingestion pipeline.

Takes PDF research papers, extracts text with section awareness,
chunks them, embeds via Voyage AI, and stores in Supabase.

Note: uses sync Supabase client inside async functions. Fine for CLI scripts.
Wrap DB calls in asyncio.to_thread() if ever called from web request handlers.
"""

import hashlib
import logging
import re
from statistics import median

import fitz  # pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.embedding_provider import embed_texts
from src.db import get_supabase
from src.schema.rag import PaperMetadata, PaperResponse
from src.utils.config import config

logger = logging.getLogger(__name__)

# Known academic section headers (case-insensitive matching)
KNOWN_SECTIONS = {
    "abstract", "introduction", "background", "methods", "methodology",
    "materials and methods", "results", "discussion", "conclusion",
    "conclusions", "references", "acknowledgements", "acknowledgments",
    "limitations", "future work", "related work", "literature review",
    "experimental design", "study design", "statistical analysis",
    "data analysis", "findings", "implications", "supplementary",
    "appendix",
}


def compute_content_hash(pdf_path: str) -> str:
    """SHA-256 hash of raw PDF bytes for deduplication."""
    with open(pdf_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def extract_sections(pdf_path: str) -> list[dict]:
    """Extract text from PDF with section awareness and page tracking.

    Uses pymupdf font analysis to detect section headers (font size > 1.2x
    median body font). Known section keywords boost detection confidence.
    Falls back to a single section if no headers are detected.

    Returns list of:
        {
            "section": str | None,
            "text": str,
            "page_map": [(char_offset, page_number), ...]
        }
    where page_map tracks which page each character came from,
    enabling accurate per-chunk page numbers after splitting.
    """
    doc = fitz.open(pdf_path)

    # --- First pass: collect font sizes to compute median ---
    all_font_sizes: list[float] = []
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] != 0:  # skip image blocks
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        all_font_sizes.append(span["size"])

    if not all_font_sizes:
        doc.close()
        return [{"section": None, "text": "", "page_map": []}]

    median_size = median(all_font_sizes)
    header_threshold = median_size * 1.2

    # --- Second pass: extract text blocks with header detection ---
    # Each block becomes (text, page_number, is_header)
    text_blocks: list[tuple[str, int, bool]] = []

    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] != 0:
                continue

            # --- Check for inline "Abstract:" label ---
            # Some journals format abstract as a single block:
            #   "Abstract: The full abstract text here..."
            # where "Abstract:" is bold and the rest is regular.
            # Split into a header block + body block.
            first_span = None
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["text"].strip():
                        first_span = span
                        break
                if first_span:
                    break

            if first_span:
                first_text = first_span["text"].strip().rstrip(":").lower()
                if first_text == "abstract" and (first_span["flags"] & 16):
                    # Emit "Abstract" as a header
                    text_blocks.append(("Abstract", page_num, True))
                    # Collect remaining text as body
                    body_parts: list[str] = []
                    skip_first = True
                    for line in block["lines"]:
                        for span in line["spans"]:
                            t = span["text"].strip()
                            if not t:
                                continue
                            if skip_first:
                                # Remove "Abstract:" prefix from first span
                                stripped = re.sub(r"^[Aa]bstract:?\s*", "", span["text"]).strip()
                                if stripped:
                                    body_parts.append(stripped)
                                skip_first = False
                            else:
                                body_parts.append(t)
                    body_text = " ".join(body_parts).strip()
                    if body_text:
                        text_blocks.append((body_text, page_num, False))
                    continue

            block_text_parts: list[str] = []
            block_max_font: float = 0
            block_is_bold = True  # assume bold until proven otherwise

            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        block_text_parts.append(text)
                        block_max_font = max(block_max_font, span["size"])
                        # pymupdf flags: bit 4 (16) = bold
                        if not (span["flags"] & 16):
                            block_is_bold = False

            block_text = " ".join(block_text_parts).strip()
            if not block_text:
                continue

            # Detect headers via three signals:
            # 1. Large font (>= 1.2x median) + short text
            # 2. Bold + short text + known section keyword
            # 3. Bold + short text + top-level numbered pattern (e.g. "3. Topic Name")
            is_header = False
            if len(block_text) < 100:
                # Normalize: lowercase, strip punctuation, strip leading numbers
                # "1. Introduction" → "introduction", "3.2 Results" → "results"
                normalized = block_text.lower().strip().rstrip(".:;")
                normalized = re.sub(r"^[\d]+\.?\d*\.?\s*", "", normalized)

                # Check if text starts with a top-level number pattern (e.g. "3.", "12.")
                # but NOT a sub-section (e.g. "3.1", "3.1.2")
                is_top_level_numbered = bool(re.match(r"^\d+\.\s+\S", block_text))

                if block_max_font >= header_threshold:
                    # Large font + short text = header (keyword match optional)
                    is_header = True
                elif block_is_bold and normalized in KNOWN_SECTIONS:
                    # Same-size bold font + known keyword = header
                    is_header = True
                elif block_is_bold and is_top_level_numbered:
                    # Same-size bold font + "3. Something" pattern = major section
                    is_header = True

            text_blocks.append((block_text, page_num, is_header))

    doc.close()

    # --- Group blocks into sections ---
    # Count detected headers
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

    # Multiple headers detected — group into sections
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
    chunk_index = 0

    for section in sections:
        section_text = section["text"]
        if not section_text.strip():
            continue

        splits = splitter.split_text(section_text)

        for split_text in splits:
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
