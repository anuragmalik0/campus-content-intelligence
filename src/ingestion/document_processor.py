"""
Document/Slide Processor
Layer 1 — Ingestion
Owner: Person 3 (Image/Slide/PDF Processing)

Extracts text and structure from lecture notes PDFs and slide decks into standardized
Chunk objects as defined in system-design.md:

Chunk Contract:
{
    "id":            str,    # stable, unique, derived slug: f"{slug(source_name)}-page-{location}-{chunk_idx}"
    "text":          str,    # actual paragraph or slide content
    "source_type":   str,    # "pdf" | "slide"
    "source_name":   str,    # human-readable name, e.g. "Lecture 3 Notes — Optimization"
    "location":      str,    # string page number: "1", "2", ...
    "location_kind": str     # always "page" for documents and slides
}

Extraction Strategy:
- Plain text PDFs: local extraction via PyPDF2 / pypdf is fast, free, and runs offline.
- Per-page text is split by paragraph boundaries so chunks are focused units of meaning.
- Every chunk preserves its exact page number for accurate citations.
"""

import os
import re
import json
from typing import TypedDict
from dotenv import load_dotenv
from PyPDF2 import PdfReader

load_dotenv()

# Schema type for static analysis and documentation
class Chunk(TypedDict):
    id: str
    text: str
    source_type: str
    source_name: str
    location: str
    location_kind: str


def slugify(text: str) -> str:
    """Generate a URL-safe, clean identifier slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def generate_chunk_id(source_name: str, location_kind: str, location: str, chunk_index: int = 0) -> str:
    """
    Generate a derived, deterministic ID for a chunk.
    Avoids random IDs so re-indexing overwrites rather than duplicates chunks.
    """
    source_slug = slugify(source_name)
    loc_slug = slugify(str(location))
    return f"{source_slug}-{location_kind}-{loc_slug}-{chunk_index}"


def split_page_into_paragraphs(page_text: str, min_chars: int = 80, max_chars: int = 1200) -> list[str]:
    """
    Splits page text into coherent paragraph-sized chunks.
    - Merges tiny paragraphs (e.g. single headers) with subsequent text.
    - Avoids returning fragmented single sentences or oversized multi-topic walls of text.
    """
    # Normalize line endings
    clean_text = page_text.replace("\r\n", "\n").strip()
    if not clean_text:
        return []

    # Split by blank lines or multiple newlines
    raw_paragraphs = [p.strip() for p in re.split(r'\n\s*\n', clean_text) if p.strip()]

    chunks = []
    current_buf = []
    current_len = 0

    for para in raw_paragraphs:
        # Collapse internal single line breaks into spaces
        para_single_line = " ".join(para.split())
        para_len = len(para_single_line)

        # If adding this paragraph exceeds max_chars and we already have text, flush buffer
        if current_buf and (current_len + para_len > max_chars):
            chunks.append(" ".join(current_buf))
            current_buf = [para_single_line]
            current_len = para_len
        else:
            current_buf.append(para_single_line)
            current_len += para_len

        # If current buffer is sufficiently large, flush it
        if current_len >= min_chars and current_len >= 500:
            chunks.append(" ".join(current_buf))
            current_buf = []
            current_len = 0

    if current_buf:
        remaining = " ".join(current_buf)
        # If remaining is too small and we have a previous chunk, merge with it
        if len(remaining) < min_chars and chunks:
            chunks[-1] = chunks[-1] + " " + remaining
        else:
            chunks.append(remaining)

    return chunks if chunks else [" ".join(clean_text.split())]


def extract_pdf_content(pdf_path: str, source_name: str) -> list[Chunk]:
    """
    Extracts content from a text-based PDF document (e.g. lecture notes).
    Splits each page into paragraph chunks, attaching the 1-indexed page number.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF document not found: {pdf_path}")

    reader = PdfReader(pdf_path)
    chunks: list[Chunk] = []

    for page_idx, page in enumerate(reader.pages):
        page_num = str(page_idx + 1)
        raw_text = page.extract_text() or ""
        
        paragraphs = split_page_into_paragraphs(raw_text)
        for chunk_idx, para_text in enumerate(paragraphs):
            chunk_id = generate_chunk_id(source_name, "page", page_num, chunk_idx)
            chunk: Chunk = {
                "id": chunk_id,
                "text": para_text,
                "source_type": "pdf",
                "source_name": source_name,
                "location": page_num,
                "location_kind": "page"
            }
            chunks.append(chunk)

    return chunks


def extract_slide_content(slide_pdf_path: str, source_name: str) -> list[Chunk]:
    """
    Extracts content from a slide deck PDF where each PDF page represents one slide.
    Each slide is treated as an individual chunk with location = slide number.
    """
    if not os.path.exists(slide_pdf_path):
        raise FileNotFoundError(f"Slide deck not found: {slide_pdf_path}")

    reader = PdfReader(slide_pdf_path)
    chunks: list[Chunk] = []

    for page_idx, page in enumerate(reader.pages):
        slide_num = str(page_idx + 1)
        raw_text = page.extract_text() or ""
        clean_text = " ".join(raw_text.split()).strip()

        if clean_text:
            chunk_id = generate_chunk_id(source_name, "page", slide_num, 0)
            chunk: Chunk = {
                "id": chunk_id,
                "text": clean_text,
                "source_type": "slide",
                "source_name": source_name,
                "location": slide_num,
                "location_kind": "page"
            }
            chunks.append(chunk)

    return chunks


def extract_text_file_content(file_path: str, source_name: str, source_type: str = "notes") -> list[Chunk]:
    """
    Extracts content from a plain text or markdown document (e.g. campus policies, guidelines).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Text file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    paragraphs = split_page_into_paragraphs(raw_text, min_chars=30)
    chunks: list[Chunk] = []

    for chunk_idx, para in enumerate(paragraphs):
        sec_num = str(chunk_idx + 1)
        chunk_id = generate_chunk_id(source_name, "section", sec_num, chunk_idx)
        chunk: Chunk = {
            "id": chunk_id,
            "text": para,
            "source_type": source_type,
            "source_name": source_name,
            "location": sec_num,
            "location_kind": "section"
        }
        chunks.append(chunk)

    return chunks


def save_extracted_chunks(chunks: list[Chunk], output_path: str) -> None:
    """Writes extracted chunks to disk as JSON (the Phase 1-2 cache boundary)."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"[CACHE] Saved {len(chunks)} chunks to {output_path}")


def load_cached_chunks(cache_path: str) -> list[Chunk]:
    """Loads extracted chunks from disk cache."""
    if not os.path.exists(cache_path):
        raise FileNotFoundError(f"Cache file not found: {cache_path}")
    with open(cache_path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import sys

    # Determine base project dir whether run directly or as module
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))

    media_dir = os.path.join(project_root, "data", "sample_media")
    notes_path = os.path.join(media_dir, "neural_networks_notes.pdf")
    slides_path = os.path.join(media_dir, "neural_networks_slides.pdf")
    policy_path = os.path.join(media_dir, "attendance_criteria.txt")
    cache_path = os.path.join(project_root, "data", "cache", "extracted_documents.json")

    print(f"Running Document Processor on sample media in: {media_dir}")
    all_chunks: list[Chunk] = []

    if os.path.exists(notes_path):
        print(f"\n--- Ingesting Lecture Notes: {notes_path} ---")
        note_chunks = extract_pdf_content(notes_path, source_name="Lecture 3 Notes: Gradient Descent")
        print(f"Extracted {len(note_chunks)} chunks from notes.")
        all_chunks.extend(note_chunks)

    if os.path.exists(slides_path):
        print(f"\n--- Ingesting Slides: {slides_path} ---")
        slide_chunks = extract_slide_content(slides_path, source_name="Lecture 3 Slides: Optimization Landscape")
        print(f"Extracted {len(slide_chunks)} chunks from slides.")
        all_chunks.extend(slide_chunks)

    if os.path.exists(policy_path):
        print(f"\n--- Ingesting Campus Attendance Policy: {policy_path} ---")
        policy_chunks = extract_text_file_content(policy_path, source_name="Campus Attendance Policy", source_type="notes")
        print(f"Extracted {len(policy_chunks)} chunks from campus policy.")
        all_chunks.extend(policy_chunks)

    if all_chunks:
        save_extracted_chunks(all_chunks, cache_path)
        print(f"\nTotal extracted document chunks saved: {len(all_chunks)}")
        print("\n--- Spot-check last chunk ---")
        last_c = all_chunks[-1]
        print(f"ID: {last_c['id']}")
        print(f"Source: {last_c['source_name']} ({last_c['source_type']}) - {last_c['location_kind']} {last_c['location']}")
        print(f"Text preview: {last_c['text']}")

