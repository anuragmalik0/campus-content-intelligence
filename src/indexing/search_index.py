"""
Search Index Builder & Retrieval Engine
Layer 2 — Indexing
Owner: Person 4 (Indexing & Retrieval)

Loads extracted Chunks from Layer 1 disk caches and manages search retrieval.
Implements the seam:
    search(query: str, top: int = 5) -> list[Chunk]

Contract conforming to system-design.md:
- Search schema mirrors the unified Chunk contract (id, text, source_type, source_name, location, location_kind).
- Each returned chunk includes a relevance 'score' for Layer 3 confidence/refusal decisions.
- Azure AI Search backend when credentials are present in .env.
- Built-in local BM25 keyword engine when running offline or testing on the shared laptop.
"""

import os
import re
import math
import json
from typing import TypedDict, Optional
from dotenv import load_dotenv

load_dotenv()

class SearchHit(TypedDict):
    id: str
    text: str
    source_type: str
    source_name: str
    location: str
    location_kind: str
    score: float


SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "").strip()
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "").strip()
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "campus-content-index").strip()


def is_azure_search_configured() -> bool:
    """Checks whether valid Azure AI Search credentials are configured."""
    return bool(
        SEARCH_ENDPOINT
        and SEARCH_KEY
        and "<your-" not in SEARCH_ENDPOINT
        and "your-key" not in SEARCH_KEY
    )


# ---------------------------------------------------------------------------
# Local In-Memory BM25 Search Engine (for offline testing & development)
# ---------------------------------------------------------------------------

class LocalBM25Index:
    """
    Lightweight, deterministic BM25 keyword search engine for local offline execution.
    Requires no external services or extra dependencies.
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: list[dict] = []
        self.doc_lens: list[int] = []
        self.avg_doc_len: float = 0.0
        self.doc_freqs: dict[str, int] = {}
        self.idf: dict[str, float] = {}

    def _tokenize(self, text: str) -> list[str]:
        return [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_]+\b', text)]

    def index(self, documents: list[dict]) -> None:
        self.corpus = documents
        num_docs = len(documents)
        if num_docs == 0:
            return

        self.doc_lens = []
        self.doc_freqs = {}

        for doc in documents:
            tokens = self._tokenize(doc.get("text", ""))
            self.doc_lens.append(len(tokens))
            seen_words = set(tokens)
            for word in seen_words:
                self.doc_freqs[word] = self.doc_freqs.get(word, 0) + 1

        self.avg_doc_len = sum(self.doc_lens) / max(1, num_docs)

        # Standard BM25 idf with floor protection
        self.idf = {}
        for word, freq in self.doc_freqs.items():
            val = math.log(1.0 + (num_docs - freq + 0.5) / (freq + 0.5))
            self.idf[word] = max(0.1, val)

    def search(self, query: str, top: int = 5) -> list[SearchHit]:
        query_tokens = self._tokenize(query)
        if not query_tokens or not self.corpus:
            return []

        scores: list[float] = [0.0] * len(self.corpus)

        for i, doc in enumerate(self.corpus):
            doc_tokens = self._tokenize(doc.get("text", ""))
            doc_len = self.doc_lens[i]
            # Term frequencies in document
            tf: dict[str, int] = {}
            for t in doc_tokens:
                tf[t] = tf.get(t, 0) + 1

            doc_score = 0.0
            for q_term in query_tokens:
                if q_term in tf:
                    term_freq = tf[q_term]
                    idf_val = self.idf.get(q_term, 0.1)
                    denom = term_freq + self.k1 * (1.0 - self.b + self.b * (doc_len / max(1.0, self.avg_doc_len)))
                    doc_score += idf_val * (term_freq * (self.k1 + 1.0)) / max(0.001, denom)

            scores[i] = doc_score

        # Pair with documents and sort descending
        scored_docs = []
        for doc, score in zip(self.corpus, scores):
            if score > 0:
                hit: SearchHit = {
                    "id": doc.get("id", ""),
                    "text": doc.get("text", ""),
                    "source_type": doc.get("source_type", ""),
                    "source_name": doc.get("source_name", ""),
                    "location": doc.get("location", ""),
                    "location_kind": doc.get("location_kind", ""),
                    "score": round(score, 4)
                }
                scored_docs.append(hit)

        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[:top]


# Global singleton instance for local index
_local_index = LocalBM25Index()


# ---------------------------------------------------------------------------
# Azure AI Search Management
# ---------------------------------------------------------------------------

def create_search_index():
    """Create or update the Azure AI Search index conforming to the Chunk contract."""
    if not is_azure_search_configured():
        print("[INFO] Azure AI Search not configured in .env. Using local BM25 index.")
        return

    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        SearchIndex,
        SimpleField,
        SearchableField,
        SearchFieldDataType,
    )

    index_client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT, credential=AzureKeyCredential(SEARCH_KEY)
    )

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="text", type=SearchFieldDataType.String),
        SimpleField(name="source_type", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="source_name", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="location", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="location_kind", type=SearchFieldDataType.String, filterable=True),
    ]

    index = SearchIndex(name=INDEX_NAME, fields=fields)
    index_client.create_or_update_index(index)
    print(f"[AZURE] Search index '{INDEX_NAME}' created/updated successfully.")


def upload_chunks(chunks: list[dict]) -> int:
    """
    Loads chunks into search storage.
    Pushes to Azure AI Search if credentials are live, and always updates the local index.
    """
    if not chunks:
        print("[WARN] No chunks provided to upload.")
        return 0

    # Always index into local BM25 engine
    _local_index.index(chunks)

    # If Azure is configured and not a managed Foundry knowledge index, push to remote cloud index
    if is_azure_search_configured() and not INDEX_NAME.startswith("ks-"):
        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient

            # Ensure index exists on Azure before uploading documents
            create_search_index()

            search_client = SearchClient(
                endpoint=SEARCH_ENDPOINT,
                index_name=INDEX_NAME,
                credential=AzureKeyCredential(SEARCH_KEY)
            )
            # Azure expects dict with keys matching fields
            azure_docs = [
                {
                    "id": c["id"],
                    "text": c["text"],
                    "source_type": c["source_type"],
                    "source_name": c["source_name"],
                    "location": str(c["location"]),
                    "location_kind": c["location_kind"],
                }
                for c in chunks
            ]
            result = search_client.upload_documents(documents=azure_docs)
            print(f"[AZURE] Uploaded {len(azure_docs)} chunks to index '{INDEX_NAME}'.")
        except Exception as e:
            print(f"[WARN] Azure Search upload could not reach endpoint: {e}. Using local search index.")

    return len(chunks)


def load_cached_chunks_and_index() -> int:
    """
    Finds all cached chunk files in data/cache/ and indexes them.
    Returns total chunks indexed.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    cache_dir = os.path.join(project_root, "data", "cache")

    all_chunks = []
    if os.path.exists(cache_dir):
        for fname in os.listdir(cache_dir):
            if fname.endswith(".json") and fname.startswith("extracted_"):
                fpath = os.path.join(cache_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        all_chunks.extend(data)
                        print(f"Loaded {len(data)} chunks from {fname}")
                except Exception as e:
                    print(f"Error loading {fpath}: {e}")

    return upload_chunks(all_chunks)


def search(query: str, top: int = 5, min_score: float = 0.0) -> list[SearchHit]:
    """
    Core retrieval seam for Layer 3 (orchestrator.py).
    Takes a natural language query string and returns top-matching Chunks with scores.
    """
    # Ensure local index is populated if empty
    if not _local_index.corpus:
        load_cached_chunks_and_index()

    if is_azure_search_configured():
        try:
            import urllib.parse
            import requests

            url = f"{SEARCH_ENDPOINT}/indexes/{INDEX_NAME}/docs?api-version=2023-11-01&search={urllib.parse.quote(query)}&$top={top}"
            resp = requests.get(url, headers={"api-key": SEARCH_KEY}, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("value", [])
                hits: list[SearchHit] = []
                for r in data:
                    score = float(r.get("@search.score", 1.0))
                    if score >= min_score:
                        text = r.get("snippet") or r.get("text") or ""
                        source = r.get("metadata_storage_path") or r.get("source_name") or "attendance.txt"
                        loc = r.get("location") or "snippet"
                        hits.append({
                            "id": r.get("uid") or r.get("id") or "doc",
                            "text": text,
                            "source_type": "foundry_kb",
                            "source_name": source,
                            "location": loc,
                            "location_kind": "section",
                            "score": round(score, 4)
                        })
                if hits:
                    return hits
            else:
                print(f"[WARN] Azure Search REST error {resp.status_code}: {resp.text[:120]}")
        except Exception as e:
            print(f"[WARN] Azure Search error: {e}. Falling back to local index.")

    # Local BM25 fallback
    results = _local_index.search(query, top=top)
    return [r for r in results if r["score"] >= min_score]


if __name__ == "__main__":
    print("=" * 60)
    print("  Phase 3 — Search Index & Retrieval Demo")
    print("=" * 60)

    total = load_cached_chunks_and_index()
    print(f"\nTotal indexed chunks: {total}")

    sample_queries = [
        "What is the update formula for gradient descent?",
        "Why are ravines hard for gradient descent?",
        "What is the physical intuition for Momentum?",
        "What is the capital of Australia?"
    ]

    print("\n--- Running Sample Retrieval Queries ---")
    for q in sample_queries:
        print(f"\nQuery: '{q}'")
        hits = search(q, top=3)
        if not hits:
            print("  [NO MATCHES FOUND]")
        for i, hit in enumerate(hits, 1):
            cite = f"{hit['source_name']} ({hit['source_type']}) @ {hit['location']}"
            print(f"  [{i}] Score: {hit['score']:6.2f} | {cite}")
            print(f"      {hit['text'][:110]}...")
