"""
Document Ingestion & Azure AI Search Live Indexer
Extracts content from user-uploaded PDFs, Word documents, and text files,
and indexes them directly into the live Azure AI Search cloud index (ks-file-41-index).
"""

import os
import io
import re
import json
import uuid
import requests
from pathlib import Path
from typing import Tuple, List, Dict, Any
from dotenv import load_dotenv

load_dotenv(override=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_FILE = PROJECT_ROOT / "data" / "uploaded_documents_manifest.json"


def get_search_config() -> Tuple[str, str, str]:
    """Dynamically get Azure AI Search credentials from environment."""
    load_dotenv(override=True)
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").strip().rstrip("/")
    key = os.getenv("AZURE_SEARCH_KEY", "").strip()
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "ks-file-41-index").strip()
    return endpoint, key, index_name


def get_doc_intelligence_config() -> Tuple[str, str]:
    """Dynamically get Azure AI Document Intelligence credentials from environment."""
    load_dotenv(override=True)
    endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT", "").strip().rstrip("/")
    key = os.getenv("DOCUMENT_INTELLIGENCE_KEY", "").strip()

    # Fallback to Foundry endpoint/key if not explicitly specified
    if not endpoint:
        foundry_ep = os.getenv("FOUNDRY_ENDPOINT", "").strip().rstrip("/")
        if foundry_ep:
            endpoint = foundry_ep.replace(".openai.azure.com", ".cognitiveservices.azure.com")
    if not key:
        key = os.getenv("FOUNDRY_API_KEY", "").strip()

    return endpoint, key


def is_doc_intelligence_configured() -> bool:
    """Check whether Azure Document Intelligence endpoint and key are available."""
    endpoint, key = get_doc_intelligence_config()
    return bool(endpoint and key and "<your-" not in endpoint)


def extract_with_azure_document_intelligence(file_bytes: bytes, filename: str) -> List[Tuple[str, str]]:
    """
    Parses document bytes using Azure AI Document Intelligence (prebuilt-layout model).
    Accurately extracts text, headers, paragraphs, and page numbers with cloud OCR and layout analysis.
    Returns: list of (location_str, text)
    """
    endpoint, key = get_doc_intelligence_config()
    if not (endpoint and key):
        raise RuntimeError("Azure Document Intelligence credentials not configured.")

    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        content_type = "application/pdf"
    elif ext in (".docx", ".doc"):
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif ext in (".jpg", ".jpeg"):
        content_type = "image/jpeg"
    elif ext == ".png":
        content_type = "image/png"
    elif ext in (".txt", ".md", ".csv", ".json"):
        content_type = "text/plain; charset=utf-8"
    else:
        content_type = "application/octet-stream"

    analyze_url = f"{endpoint}/formrecognizer/documentModels/prebuilt-layout:analyze?api-version=2023-07-31"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": content_type
    }

    try:
        post_res = requests.post(analyze_url, headers=headers, data=file_bytes, timeout=25)
        if post_res.status_code not in (200, 202):
            raise RuntimeError(f"Azure Document Intelligence returned status {post_res.status_code}: {post_res.text[:150]}")

        op_url = post_res.headers.get("Operation-Location")
        if not op_url:
            raise RuntimeError("Azure Document Intelligence did not return Operation-Location header.")

        # Poll operation for completion
        import time
        max_retries = 30
        poll_headers = {"Ocp-Apim-Subscription-Key": key}

        for _ in range(max_retries):
            time.sleep(1.2)
            poll_res = requests.get(op_url, headers=poll_headers, timeout=12)
            if poll_res.status_code == 200:
                poll_data = poll_res.json()
                status = poll_data.get("status")
                if status == "succeeded":
                    analyze_result = poll_data.get("analyzeResult", {})
                    paragraphs = analyze_result.get("paragraphs", [])

                    if not paragraphs:
                        content = analyze_result.get("content", "").strip()
                        return [("page 1", content)] if content else []

                    # Group paragraphs by page
                    page_groups: Dict[int, List[str]] = {}
                    for p in paragraphs:
                        text = p.get("content", "").strip()
                        if not text:
                            continue
                        regions = p.get("boundingRegions", [])
                        page_num = regions[0].get("pageNumber", 1) if regions else 1
                        page_groups.setdefault(page_num, []).append(text)

                    sections = []
                    for page_num in sorted(page_groups.keys()):
                        combined_text = "\n\n".join(page_groups[page_num])
                        sections.append((f"page {page_num}", combined_text))

                    return sections
                elif status == "failed":
                    err = poll_data.get("error", {}).get("message", "Document analysis failed.")
                    raise RuntimeError(f"Azure Document Intelligence processing failed: {err}")
            else:
                print(f"[WARN] Polling returned status {poll_res.status_code}")

        raise TimeoutError("Azure Document Intelligence analysis timed out.")
    except Exception as e:
        print(f"[WARN] Azure Document Intelligence error ({e}).")
        raise



def load_manifest() -> Dict[str, Any]:
    """Load local manifest of user-uploaded files."""
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_manifest(manifest: Dict[str, Any]) -> None:
    """Save local manifest of user-uploaded files."""
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def slugify(text: str) -> str:
    """Clean string into URL-safe slug."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def extract_text_from_pdf(file_bytes: bytes) -> List[Tuple[str, str]]:
    """
    Extracts text per page from PDF bytes using pypdf.
    Returns: list of (location_str, text)
    """
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append((f"page {idx}", text))
    return pages


def extract_text_from_docx(file_bytes: bytes) -> List[Tuple[str, str]]:
    """
    Extracts text paragraphs from DOCX bytes using python-docx.
    Returns: list of (location_str, text)
    """
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    # Group paragraphs into logical sections of ~500-1000 characters
    sections = []
    buf = []
    buf_len = 0
    sec_idx = 1
    
    for p in paragraphs:
        buf.append(p)
        buf_len += len(p)
        if buf_len >= 600:
            sections.append((f"section {sec_idx}", "\n\n".join(buf)))
            sec_idx += 1
            buf = []
            buf_len = 0
            
    if buf:
        sections.append((f"section {sec_idx}", "\n\n".join(buf)))
        
    return sections


def extract_text_from_txt(file_bytes: bytes) -> List[Tuple[str, str]]:
    """
    Extracts text from plain text or markdown files.
    Returns: list of (location_str, text)
    """
    try:
        raw_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raw_text = file_bytes.decode("latin-1", errors="replace")
        
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw_text) if p.strip()]
    sections = []
    buf = []
    buf_len = 0
    sec_idx = 1
    
    for p in paragraphs:
        buf.append(p)
        buf_len += len(p)
        if buf_len >= 500:
            sections.append((f"part {sec_idx}", "\n\n".join(buf)))
            sec_idx += 1
            buf = []
            buf_len = 0
            
    if buf:
        sections.append((f"part {sec_idx}", "\n\n".join(buf)))
        
    return sections


def chunk_document(file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Extracts and chunks document into search-ready units.
    Uses Azure AI Document Intelligence (prebuilt-layout) as primary cloud parser,
    with seamless local offline fallback.
    Returns: (chunks, parser_name)
    """
    sections = []
    parser_used = "Local Parser"

    # 1. Primary parser: Azure AI Document Intelligence (Cloud OCR & Layout)
    if is_doc_intelligence_configured():
        try:
            print(f"[INFO] Parsing '{filename}' using Azure AI Document Intelligence...")
            sections = extract_with_azure_document_intelligence(file_bytes, filename)
            if sections:
                parser_used = "Azure AI Document Intelligence (prebuilt-layout)"
                print(f"[SUCCESS] Extracted {len(sections)} sections via Azure Document Intelligence.")
        except Exception as e:
            print(f"[WARN] Azure Document Intelligence parsing error: {e}. Using fallback.")

    # 2. Fallback: Local extractor if Document Intelligence was not used or failed
    if not sections:
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            sections = extract_text_from_pdf(file_bytes)
            parser_used = "Local PyPDF Parser (Fallback)"
        elif ext in (".docx", ".doc"):
            sections = extract_text_from_docx(file_bytes)
            parser_used = "Local python-docx Parser (Fallback)"
        else:
            sections = extract_text_from_txt(file_bytes)
            parser_used = "Local Text Parser (Fallback)"

    if not sections:
        raise ValueError(f"No readable text could be extracted from '{filename}'.")


    chunks = []
    base_slug = slugify(Path(filename).stem)

    for sec_loc, sec_text in sections:
        # Split section into chunks of max 800 chars
        words = sec_text.split()
        if len(words) <= 120:
            chunk_text = sec_text
            cid = f"up-{base_slug}-{slugify(sec_loc)}-{len(chunks)}"
            chunks.append({
                "uid": cid,
                "snippet": chunk_text,
                "metadata_storage_path": filename,
                "h1_header": filename,
                "h2_header": sec_loc,
                "location": sec_loc
            })
        else:
            # Segment large section into paragraph chunks
            sub_chunks = []
            current_words = []
            for w in words:
                current_words.append(w)
                if len(current_words) >= 90:
                    sub_chunks.append(" ".join(current_words))
                    current_words = []
            if current_words:
                sub_chunks.append(" ".join(current_words))

            for sub_idx, sub_text in enumerate(sub_chunks):
                cid = f"up-{base_slug}-{slugify(sec_loc)}-{len(chunks)}-{sub_idx}"
                chunks.append({
                    "uid": cid,
                    "snippet": sub_text,
                    "metadata_storage_path": filename,
                    "h1_header": filename,
                    "h2_header": sec_loc,
                    "location": sec_loc
                })

    return chunks, parser_used



def index_chunks_to_azure_search(chunks: List[Dict[str, Any]]) -> Tuple[bool, int, str]:
    """
    Pushes document chunks directly into the live Azure AI Search cloud index via REST API.
    Returns: (success: bool, count: int, message: str)
    """
    endpoint, key, index_name = get_search_config()
    if not (endpoint and key and index_name):
        return False, 0, "Azure AI Search credentials are missing from .env."

    url = f"{endpoint}/indexes/{index_name}/docs/index?api-version=2024-07-01"
    headers = {
        "api-key": key,
        "Content-Type": "application/json"
    }

    # Format documents according to ks-file-41-index schema
    azure_docs = []
    for c in chunks:
        azure_docs.append({
            "@search.action": "upload",
            "uid": c["uid"],
            "snippet": c["snippet"],
            "metadata_storage_path": c["metadata_storage_path"],
            "h1_header": c.get("h1_header", ""),
            "h2_header": c.get("h2_header", "")
        })

    # Batch in groups of 100
    batch_size = 100
    indexed_count = 0

    for i in range(0, len(azure_docs), batch_size):
        batch = azure_docs[i:i + batch_size]
        payload = {"value": batch}

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            if res.status_code in (200, 201):
                res_data = res.json()
                for item in res_data.get("value", []):
                    if item.get("status") is True:
                        indexed_count += 1
            else:
                err_msg = f"Azure Search returned status {res.status_code}: {res.text[:200]}"
                print(f"[WARN] {err_msg}")
                return False, indexed_count, err_msg
        except Exception as e:
            print(f"[ERROR] Failed to push chunks to Azure Search: {e}")
            return False, indexed_count, str(e)

    return True, indexed_count, f"Successfully indexed {indexed_count} chunks into Azure AI Search index '{index_name}'."


def delete_document_from_azure_search(filename: str) -> Tuple[bool, str]:
    """
    Deletes all chunks belonging to the given filename from Azure AI Search cloud index.
    """
    endpoint, key, index_name = get_search_config()
    if not (endpoint and key and index_name):
        return False, "Azure AI Search credentials not configured."

    # First, query all chunk uids for this filename
    search_url = f"{endpoint}/indexes/{index_name}/docs?api-version=2024-07-01&search=*&$filter=metadata_storage_path eq '{filename}'&$select=uid&$top=500"
    headers = {
        "api-key": key,
        "Content-Type": "application/json"
    }

    uids_to_delete = []
    try:
        search_res = requests.get(search_url, headers=headers, timeout=12)
        if search_res.status_code == 200:
            docs = search_res.json().get("value", [])
            uids_to_delete = [d["uid"] for d in docs if "uid" in d]
        else:
            print(f"[WARN] Search query for delete returned status {search_res.status_code}")
    except Exception as e:
        print(f"[WARN] Failed to query uids for deletion: {e}")

    # Fallback to local manifest if search filter didn't catch all
    manifest = load_manifest()
    if filename in manifest:
        stored_uids = manifest[filename].get("uids", [])
        uids_to_delete = list(set(uids_to_delete + stored_uids))

    if not uids_to_delete:
        # Clean from manifest anyway
        if filename in manifest:
            del manifest[filename]
            save_manifest(manifest)
        return True, f"No chunks found in index for '{filename}', manifest cleaned."

    # Issue delete action
    index_url = f"{endpoint}/indexes/{index_name}/docs/index?api-version=2024-07-01"
    del_payload = {
        "value": [{"@search.action": "delete", "uid": uid} for uid in uids_to_delete]
    }

    try:
        del_res = requests.post(index_url, headers=headers, json=del_payload, timeout=15)
        if del_res.status_code in (200, 201):
            if filename in manifest:
                del manifest[filename]
                save_manifest(manifest)
            return True, f"Successfully deleted {len(uids_to_delete)} chunks for '{filename}' from Azure AI Search."
        else:
            return False, f"Azure Search delete failed with status {del_res.status_code}: {del_res.text[:150]}"
    except Exception as e:
        return False, f"Error deleting document from Azure Search: {e}"


def process_and_index_file(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    High-level orchestrator:
    1. Extracts and chunks the file using Azure AI Document Intelligence.
    2. Pushes chunks to Azure AI Search.
    3. Saves record in the local manifest.
    Returns: summary dict
    """
    chunks, parser_used = chunk_document(file_bytes, filename)
    if not chunks:
        raise ValueError("Document yielded 0 chunks.")

    success, indexed_count, message = index_chunks_to_azure_search(chunks)
    if not success and indexed_count == 0:
        raise RuntimeError(f"Azure Search indexing failed: {message}")

    uids = [c["uid"] for c in chunks]
    snippet_preview = chunks[0]["snippet"][:150] if chunks else ""

    manifest = load_manifest()
    manifest[filename] = {
        "filename": filename,
        "parser_used": parser_used,
        "chunk_count": len(chunks),
        "indexed_count": indexed_count,
        "uids": uids,
        "preview": snippet_preview,
        "file_size": len(file_bytes)
    }
    save_manifest(manifest)

    # Cache chunks to disk for instant quiz and agentic processing
    try:
        cache_dir = PROJECT_ROOT / "data" / "cache" / "extracted_docs"
        cache_dir.mkdir(parents=True, exist_ok=True)
        safe_cache_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename) + ".json"
        with open(cache_dir / safe_cache_name, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2)
    except Exception as err:
        print(f"[WARN] Could not cache chunks to disk: {err}")

    return {
        "success": True,
        "filename": filename,
        "parser_used": parser_used,
        "chunks_indexed": indexed_count,
        "preview": snippet_preview,
        "message": message
    }


def get_document_chunks(filename: str) -> List[Dict[str, Any]]:
    """
    Retrieves full chunks for a given document.
    Checks:
    1. Local extracted_docs cache
    2. Azure AI Search by metadata_storage_path
    3. Local data/sample_media/ or project root files
    """
    safe_cache_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename) + ".json"
    cache_path = PROJECT_ROOT / "data" / "cache" / "extracted_docs" / safe_cache_name
    if cache_path.is_file():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Check Azure AI Search
    endpoint, key, index_name = get_search_config()
    if endpoint and key and index_name:
        try:
            url = f"{endpoint}/indexes/{index_name}/docs?api-version=2024-07-01&search=*&$filter=metadata_storage_path eq '{filename}'&$top=100"
            res = requests.get(url, headers={"api-key": key, "Content-Type": "application/json"}, timeout=10)
            if res.status_code == 200:
                docs = res.json().get("value", [])
                if docs:
                    return [
                        {
                            "uid": d.get("uid", ""),
                            "snippet": d.get("snippet", ""),
                            "metadata_storage_path": filename,
                            "location": d.get("location") or d.get("h2_header") or "Document"
                        }
                        for d in docs
                    ]
        except Exception as e:
            print(f"[WARN] Error fetching chunks from Azure Search: {e}")

    # Check sample_media
    media_file = PROJECT_ROOT / "data" / "sample_media" / filename
    if media_file.is_file():
        try:
            chunks, _ = chunk_document(media_file.read_bytes(), filename)
            return chunks
        except Exception as e:
            print(f"[WARN] Error reading media file: {e}")

    # Check general cache files
    cache_dir = PROJECT_ROOT / "data" / "cache"
    if cache_dir.exists():
        for cfile in cache_dir.glob("extracted_*.json"):
            try:
                with open(cfile, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                    matching = [c for c in cdata if c.get("source_name") == filename]
                    if matching:
                        return [
                            {
                                "uid": c.get("id", ""),
                                "snippet": c.get("text", ""),
                                "metadata_storage_path": filename,
                                "location": f"{c.get('location_kind', 'section')} {c.get('location', '')}"
                            }
                            for c in matching
                        ]
            except Exception:
                pass

    return []


