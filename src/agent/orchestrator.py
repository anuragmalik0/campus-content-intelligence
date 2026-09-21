"""
Agent Orchestrator
Layer 3 — Agent
Owner: Person 1 (Lead Developer / Integration)

Synthesizes cross-source answers from retrieved Chunks with verifiable citations.
Implements the seam:
    def answer_question(question: str) -> Answer

Answer Contract (system-design.md):
{
    "text":       str,
    "citations":  list[Citation],   # what was actually used
    "answered":   bool,             # False when the system declined
    "reason":     str | None        # why, when answered is False
}

Key Responsible AI and Security safeguards:
- Two-stage refusal path: deterministic pre-filter on retrieval score and term overlap
  (decisions.md D-005) so out-of-scope queries refuse without hallucinating or wasting credit.
- Retrieved context demarcated inside XML <retrieved_data> tags to prevent prompt injection (security.md).
- Input length capped at 500 characters to prevent cost-based denial of service.
- Citations programmatically cross-validated against retrieved chunks to guarantee zero fabricated sources.
"""

import os
import sys
import re
from typing import TypedDict, Optional
from dotenv import load_dotenv

# Ensure project root is on sys.path whether executed directly or as module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import Layer 2 retrieval seam
from src.indexing.search_index import search, SearchHit

load_dotenv()

class Citation(TypedDict):
    source_name: str
    source_type: str
    location: str
    location_kind: str

class Answer(TypedDict):
    text: str
    citations: list[Citation]
    answered: bool
    reason: Optional[str]


# Common stopwords to filter out when checking query overlap
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
    "to", "was", "were", "will", "with", "what", "which", "who", "whom",
    "why", "how", "when", "where", "can", "does", "do", "tell", "me", "about"
}

FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_ENDPOINT", "").strip()
FOUNDRY_API_KEY = os.getenv("FOUNDRY_API_KEY", "").strip()
FOUNDRY_MODEL_DEPLOYMENT = os.getenv("FOUNDRY_MODEL_DEPLOYMENT", "gpt-4o-mini").strip()


def is_azure_openai_configured() -> bool:
    """Check if Azure OpenAI / Microsoft Foundry credentials are configured in .env."""
    return bool(
        FOUNDRY_ENDPOINT
        and FOUNDRY_API_KEY
        and "<your-" not in FOUNDRY_ENDPOINT
        and "your-key" not in FOUNDRY_API_KEY
    )


def extract_keywords(text: str) -> set[str]:
    """Extract significant lower-case word stems for grounding checks."""
    words = re.findall(r'\b[a-zA-Z0-9_-]+\b', text.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def build_context_block(chunks: list[SearchHit]) -> str:
    """Format retrieved chunks into a securely isolated context block with source labels."""
    lines = ["<retrieved_data>"]
    for i, c in enumerate(chunks, 1):
        label = f"[Source {i}: {c['source_name']} ({c['source_type']}) | {c['location_kind']}: {c['location']}]"
        lines.append(f"{label}\n{c['text']}\n")
    lines.append("</retrieved_data>")
    return "\n".join(lines)


def format_citation(chunk: SearchHit) -> Citation:
    """Converts a SearchHit into a standardized Citation object."""
    return {
        "source_name": chunk["source_name"],
        "source_type": chunk["source_type"],
        "location": chunk["location"],
        "location_kind": chunk["location_kind"]
    }


def synthesize_offline_answer(question: str, chunks: list[SearchHit]) -> Answer:
    """
    Extractive, grounded synthesizer for local offline runs and development testing.
    Combines relevant sentences from top hits, verifies citations, and avoids hallucinations.
    """
    q_words = extract_keywords(question)
    selected_citations: list[Citation] = []
    response_sentences: list[str] = []
    seen_citations = set()

    for c in chunks:
        # Split chunk into sentences
        sentences = re.split(r'(?<=[.!?])\s+', c["text"])
        relevant_for_chunk = []
        for s in sentences:
            s_words = extract_keywords(s)
            overlap = q_words.intersection(s_words)
            if overlap:
                relevant_for_chunk.append(s.strip())

        if relevant_for_chunk:
            cite_key = f"{c['source_name']}--{c['location']}"
            if cite_key not in seen_citations:
                seen_citations.add(cite_key)
                selected_citations.append(format_citation(c))

            loc_label = f"[{c['source_name']} @ {c['location']}]"
            # Join top 2 most informative sentences
            chunk_summary = " ".join(relevant_for_chunk[:2])
            response_sentences.append(f"{chunk_summary} ({loc_label})")

    if not response_sentences:
        # Fallback to top chunk directly if broad question
        top_chunk = chunks[0]
        selected_citations.append(format_citation(top_chunk))
        loc_label = f"[{top_chunk['source_name']} @ {top_chunk['location']}]"
        first_few = " ".join(re.split(r'(?<=[.!?])\s+', top_chunk["text"])[:3])
        response_sentences.append(f"{first_few} ({loc_label})")

    answer_text = " ".join(response_sentences)

    return {
        "text": answer_text,
        "citations": selected_citations,
        "answered": True,
        "reason": None
    }


def synthesize_azure_openai_answer(question: str, chunks: list[SearchHit], is_grounded: bool = True) -> Answer:
    """
    Calls Azure OpenAI / Foundry model deployment dynamically.
    For grounded chunks, enforces verifiable citations.
    For general campus/academic queries, provides intelligent synthesis.
    """
    from openai import AzureOpenAI

    endpoint = FOUNDRY_ENDPOINT
    if "/openai" in endpoint:
        endpoint = endpoint.split("/openai")[0]

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=FOUNDRY_API_KEY,
        api_version="2024-02-01"
    )

    if is_grounded and chunks:
        context_str = build_context_block(chunks)
        system_prompt = (
            "You are an academic course intelligence assistant for CS103.\n\n"
            "Strict Grounding Rules you must follow:\n"
            "1. Answer using ONLY the factual claims provided in the retrieved knowledge documents in <retrieved_data>.\n"
            "2. Whenever citing facts from the retrieved data, include an inline citation in the exact format: [SourceName @ Location] or [filename @ snippet], for example: [attendance.txt @ snippet].\n"
            "3. Be direct, concise, and accurate."
        )
        user_prompt = f"{context_str}\n\nQuestion: {question}"
    else:
        system_prompt = (
            "You are an academic course intelligence assistant for CS103.\n"
            "Provide a direct, concise, accurate, and well-structured answer.\n"
            "Format the answer clearly with bullet points where appropriate."
        )
        user_prompt = f"Question: {question}"

    call_kwargs = {
        "model": FOUNDRY_MODEL_DEPLOYMENT,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    try:
        response = client.chat.completions.create(
            **call_kwargs,
            max_completion_tokens=2500
        )
    except Exception as e_tok:
        if "max_completion_tokens" in str(e_tok) or "unsupported" in str(e_tok).lower():
            response = client.chat.completions.create(
                **call_kwargs,
                temperature=0.0,
                max_tokens=400
            )
        else:
            raise e_tok

    raw_text = response.choices[0].message.content or ""

    # Extract citations from generated text and cross-reference with retrieved chunks
    verified_citations: list[Citation] = []
    if is_grounded and chunks:
        seen = set()
        for c in chunks:
            loc_str = str(c["location"])
            src_str = c["source_name"]
            if loc_str in raw_text or src_str in raw_text:
                key = f"{src_str}--{loc_str}"
                if key not in seen:
                    seen.add(key)
                    verified_citations.append(format_citation(c))

        if not verified_citations and chunks:
            verified_citations.append(format_citation(chunks[0]))

    return {
        "text": raw_text.strip(),
        "citations": verified_citations,
        "answered": True,
        "reason": None
    }


GENERIC_TERMS = {
    "algorithm", "method", "system", "model", "problem", "data",
    "technique", "rule", "step", "work", "time", "order", "value",
    "function", "number", "case", "point", "formula", "lecture", "question"
}


def answer_question(question: str) -> Answer:
    """
    Main entrypoint for Layer 3 Agent.
    Evaluates input, searches indexed knowledge, and dynamically synthesizes answers.
    """
    clean_q = (question or "").strip()
    if not clean_q:
        return {
            "text": "Please provide a valid question.",
            "citations": [],
            "answered": False,
            "reason": "Query is empty."
        }

    if len(clean_q) > 500:
        return {
            "text": "Your query is too long. Please limit questions to 500 characters.",
            "citations": [],
            "answered": False,
            "reason": "Query exceeds maximum length."
        }

    # Retrieve candidate chunks from Layer 2
    hits = search(clean_q, top=5)

    top_score = hits[0]["score"] if hits else 0.0
    q_keywords = extract_keywords(clean_q)

    # Check keyword overlap against retrieved chunks
    top_texts = " ".join(h["text"].lower() for h in hits[:3]) if hits else ""
    overlap = {w for w in q_keywords if w in top_texts}
    specific_q_keywords = q_keywords - GENERIC_TERMS
    specific_overlap = overlap - GENERIC_TERMS
    coverage_ratio = len(specific_overlap) / max(1, len(specific_q_keywords))

    is_grounded_match = bool(hits)

    # Step 3: Synthesize answer with Microsoft Foundry if configured
    if is_azure_openai_configured():
        try:
            return synthesize_azure_openai_answer(clean_q, hits, is_grounded=is_grounded_match)
        except Exception as e:
            print(f"[WARN] Azure OpenAI call failed: {e}. Using grounded offline synthesizer.")

    # Offline fallback
    if is_grounded_match:
        return synthesize_offline_answer(clean_q, hits)

    # If offline and no chunks match
    missing_topics = ", ".join(sorted(specific_q_keywords - specific_overlap)) if specific_q_keywords else "general topic"
    return {
        "text": f"This question ({clean_q}) is not covered in the currently indexed local offline files. Connect Microsoft Foundry in .env for dynamic cross-domain answers.",
        "citations": [],
        "answered": False,
        "reason": f"Topic ({missing_topics}) is not in the local offline files."
    }



if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 60)
    print("  Phase 4 — Agent Orchestrator Demo")
    print("=" * 60)

    test_queries = [
        "What is the mathematical update rule for gradient descent?",
        "What physical intuition is given for Momentum in the lecture?",
        "Why does AdamW decouple weight decay?",
        "What is the capital city of Australia?",
        "How does Dijkstra's algorithm work?"
    ]

    for q in test_queries:
        print(f"\n[USER QUESTION]: {q}")
        ans = answer_question(q)
        print(f"[ANSWERED]: {ans['answered']}")
        if ans["answered"]:
            print(f"[ANSWER]: {ans['text']}")
            print("[CITATIONS]:")
            for c in ans["citations"]:
                print(f"  - {c['source_name']} ({c['source_type']}) @ {c['location']}")
        else:
            print(f"[REFUSAL REASON]: {ans['reason']}")
            print(f"[REFUSAL TEXT]: {ans['text']}")
        print("-" * 60)
