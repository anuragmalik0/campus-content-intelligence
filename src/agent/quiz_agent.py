"""
Agentic Quiz & Assessment Generator
Layer 3 — Assessment & Evaluation Agent

Analyzes uploaded documents (lecture notes, exam papers, syllabus PDFs)
using Azure AI Document Intelligence extractions and Azure AI Search chunks,
and generates structured, grounded Multiple Choice Questions (MCQs)
across configurable difficulty levels (Easy, Medium, Hard, Adaptive/Mixed).
"""

import os
import re
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

from src.services.document_indexer import get_document_chunks
from src.indexing.search_index import search

FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_ENDPOINT", "").strip()
FOUNDRY_API_KEY = os.getenv("FOUNDRY_API_KEY", "").strip()
FOUNDRY_MODEL_DEPLOYMENT = os.getenv("FOUNDRY_MODEL_DEPLOYMENT", "gpt-5-mini").strip()


def get_openai_client():
    """Initializes Azure OpenAI client using Foundry credentials."""
    from openai import AzureOpenAI

    endpoint = FOUNDRY_ENDPOINT
    if "/openai" in endpoint:
        endpoint = endpoint.split("/openai")[0]

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=FOUNDRY_API_KEY,
        api_version="2024-02-01"
    )


def extract_json_payload(raw_text: str) -> Dict[str, Any]:
    """Extracts and parses JSON object from model response, stripping any markdown wrappers."""
    cleaned = raw_text.strip()
    
    # Strip markdown code blocks ```json ... ```
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()

    # Find bounding curly braces
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1:
        cleaned = cleaned[start_idx:end_idx + 1]

    return json.loads(cleaned)


def analyze_document_knowledge(document_name: str) -> Dict[str, Any]:
    """
    Performs Phase 1 Agentic Document Understanding:
    Analyzes document text, extracts its theoretical concepts, identifies major topics,
    and detects whether existing questions/exercises are present.
    """
    # 1. Check local analysis cache
    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', document_name) + ".json"
    cache_dir = PROJECT_ROOT / "data" / "cache" / "doc_analysis"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / safe_name
    if cache_path.is_file():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # 2. Retrieve document chunks
    chunks = get_document_chunks(document_name)
    if not chunks:
        q_term = Path(document_name).stem
        search_hits = search(q_term, top=10)
        chunks = [
            {
                "uid": h.get("id"),
                "snippet": h.get("text"),
                "metadata_storage_path": h.get("source_name", document_name),
                "location": f"{h.get('location_kind', 'section')} {h.get('location', '')}"
            }
            for h in search_hits
        ]

    if not chunks:
        raise ValueError(f"No content found for document '{document_name}'.")

    # Combine document chunks up to ~25,000 chars
    doc_lines = []
    total_len = 0
    for idx, c in enumerate(chunks, 1):
        loc = c.get("location") or f"Section {idx}"
        line = f"[{document_name} @ {loc}]: {c.get('snippet', '').strip()}"
        if total_len + len(line) > 25000:
            break
        doc_lines.append(line)
        total_len += len(line)

    doc_text = "\n\n".join(doc_lines)

    system_prompt = """You are an expert academic curriculum analyst and assessment engineer.
Your job is to thoroughly analyze the provided academic document, extract its theoretical foundations, identify its major topics, and detect whether it contains existing question sets.

You must return ONLY a valid JSON object matching this schema:
{
  "document_name": "String: Name of document",
  "title": "String: Clear title or subject of the material",
  "summary": "String: 2-3 sentences providing an executive summary of the document's content",
  "topics": [
    "String: Topic 1 (e.g. Gradient Descent Dynamics)",
    "String: Topic 2 (e.g. Momentum Acceleration)",
    "String: Topic 3",
    "String: Topic 4"
  ],
  "theory_and_concepts": [
    {
      "concept": "String: Name of key theorem, formula, or concept",
      "explanation": "String: Brief 1-2 sentence theoretical explanation of how it works"
    }
  ],
  "existing_questions_found": [
    "String: Any explicit exercise, practice problem, or exam question identified in the document (or empty list if none found)"
  ],
  "recommended_quiz_focus": [
    "String: High-yield exam question theme 1",
    "String: High-yield exam question theme 2"
  ]
}
Return ONLY valid JSON with no conversational text or markdown explanation."""

    user_prompt = f"Analyze this document: {document_name}\n\n=== DOCUMENT TEXT ===\n{doc_text}\n=== END DOCUMENT TEXT ==="

    client = get_openai_client()
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
        if "max_completion_tokens" in str(e_tok):
            response = client.chat.completions.create(**call_kwargs, max_tokens=2000)
        else:
            raise e_tok

    raw_text = response.choices[0].message.content or ""
    analysis_data = extract_json_payload(raw_text)
    analysis_data["document_name"] = document_name

    # Cache result
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2)
    except Exception as err:
        print(f"[WARN] Failed to cache document analysis: {err}")

    return analysis_data


def generate_quiz(
    document_name: str,
    difficulty: str = "medium",
    count: int = 5,
    topic: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a structured educational quiz from the specified document.

    Args:
        document_name: Filename of the target document in knowledge base
        difficulty: 'easy', 'medium', 'hard', or 'mixed'
        count: Number of questions to generate (1 to 15)
        topic: Optional specific topic or chapter focus

    Returns:
        Structured quiz dict with questions, options, explanations, and citations.
    """
    count = max(1, min(15, count))
    diff = (difficulty or "medium").lower().strip()
    if diff not in ("easy", "medium", "hard", "mixed"):
        diff = "medium"

    # 1. Retrieve document content chunks
    chunks = get_document_chunks(document_name)

    # Fallback to search query if no direct chunks found
    if not chunks:
        q_term = topic if topic else Path(document_name).stem
        search_hits = search(q_term, top=10)
        chunks = [
            {
                "uid": h.get("id"),
                "snippet": h.get("text"),
                "metadata_storage_path": h.get("source_name", document_name),
                "location": f"{h.get('location_kind', 'section')} {h.get('location', '')}"
            }
            for h in search_hits
        ]

    if not chunks:
        raise ValueError(
            f"No content found for document '{document_name}'. "
            "Please ensure the document is uploaded and indexed."
        )

    # Filter by topic if specified
    if topic and len(chunks) > count * 2:
        topic_words = set(re.findall(r'\w+', topic.lower()))
        filtered = [
            c for c in chunks
            if any(w in c.get("snippet", "").lower() for w in topic_words)
        ]
        if len(filtered) >= 2:
            chunks = filtered

    # Assemble contextual source text (cap at ~8000 tokens / 32,000 chars)
    context_lines = []
    total_chars = 0
    for idx, c in enumerate(chunks, 1):
        loc = c.get("location") or f"Section {idx}"
        snip = c.get("snippet", "").strip()
        line = f"[Reference {idx}: {document_name} @ {loc}]\n{snip}\n"
        if total_chars + len(line) > 30000:
            break
        context_lines.append(line)
        total_chars += len(line)

    context_str = "\n".join(context_lines)

    # 2. Build educational assessment system prompt
    difficulty_instructions = {
        "easy": (
            "DIFFICULTY LEVEL: EASY (Foundational Recall)\n"
            "- Focus on explicit definitions, core terminology, key formulas, and direct facts.\n"
            "- The correct answer should be clearly identifiable from the text.\n"
            "- Distractors should be plausibly related terms from the field, but clearly distinguished."
        ),
        "medium": (
            "DIFFICULTY LEVEL: MEDIUM (Conceptual Comprehension & Application)\n"
            "- Focus on understanding mechanisms, cause-and-effect relationships, and comparing concepts.\n"
            "- Ask questions where the student must apply a concept or predict what happens under specific conditions.\n"
            "- Distractors should represent common student misconceptions or subtle parameter confusions."
        ),
        "hard": (
            "DIFFICULTY LEVEL: HARD (Critical Thinking & Edge Cases)\n"
            "- Focus on complex deductions, mathematical edge cases, failure modes, and architectural trade-offs.\n"
            "- Questions should require multi-step reasoning or distinguishing nuanced technical differences.\n"
            "- Distractors must be highly plausible, requiring precise conceptual mastery to eliminate."
        ),
        "mixed": (
            "DIFFICULTY LEVEL: MIXED / ADAPTIVE (Progressive Diagnostic)\n"
            f"- Generate a balanced mix: approximately 25% Easy, 50% Medium, and 25% Hard.\n"
            "- Order questions progressively from foundational to advanced."
        )
    }

    system_prompt = f"""You are an elite academic assessment agent and university examiner for computer science and AI courses.
Your task is to analyze the provided source document text and synthesize a rigorous, engaging, 100% grounded Multiple Choice Quiz (MCQ).

DOCUMENT UNDERSTANDING DIRECTIVE:
1. Examine the provided document text carefully.
2. If the document already contains questions (e.g. past paper, quiz bank, homework):
   - Extract and synthesize the core concepts being tested.
   - Formulate clear, polished question stems with 4 distinct options (A, B, C, D).
3. If the document is lecture notes, research paper, or textbook:
   - Identify key learning objectives, critical mechanisms, and definitions.
   - Formulate original, pedagogically sound questions.

{difficulty_instructions.get(diff, difficulty_instructions['medium'])}

GROUNDING & FORMAT RULES:
- Every question MUST be strictly answerable from the provided reference material. Zero external hallucination.
- Provide EXACTLY 4 options for each question (id: "A", "B", "C", "D").
- Only ONE option must be correct.
- Provide a detailed "explanation" for why the correct answer is right and why distractors are wrong.
- Provide an exact "citation" mentioning the document and section/page (e.g. "{document_name} @ Page 2").

OUTPUT FORMAT:
You MUST output ONLY a valid JSON object matching this exact schema:
{{
  "quiz_title": "String: Descriptive title for this assessment",
  "difficulty": "{diff}",
  "document_name": "{document_name}",
  "total_questions": {count},
  "summary": "String: 1-2 sentences summarizing what this quiz assesses",
  "questions": [
    {{
      "id": 1,
      "question": "String: Clear, well-formulated question stem",
      "options": [
        {{"id": "A", "text": "Option text"}},
        {{"id": "B", "text": "Option text"}},
        {{"id": "C", "text": "Option text"}},
        {{"id": "D", "text": "Option text"}}
      ],
      "correct_option": "A",
      "explanation": "String: Clear rationale explaining why A is correct and why other options are incorrect",
      "citation": "{document_name} @ location",
      "difficulty": "easy | medium | hard",
      "topic": "String: Specific subtopic"
    }}
  ]
}}
Do NOT wrap with conversational preamble. Return only the JSON object."""

    user_prompt = f"""Target Document: {document_name}
Requested Questions: {count}
Selected Difficulty: {diff.upper()}
{f'Topic Focus: {topic}' if topic else ''}

=== SOURCE DOCUMENT CONTENT ===
{context_str}
=== END OF SOURCE CONTENT ===

Generate the complete assessment JSON now:"""

    client = get_openai_client()
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
            max_completion_tokens=3500
        )
    except Exception as e_tok:
        if "max_completion_tokens" in str(e_tok):
            response = client.chat.completions.create(
                **call_kwargs,
                max_tokens=3000
            )
        else:
            raise e_tok

    raw_text = response.choices[0].message.content or ""

    try:
        quiz_data = extract_json_payload(raw_text)
    except Exception as parse_err:
        print(f"[ERROR] JSON extraction failed: {parse_err}. Raw preview: {raw_text[:300]}")
        raise ValueError(f"Failed to generate structured quiz JSON: {parse_err}")

    # Validate and normalize structure
    if "questions" not in quiz_data or not isinstance(quiz_data["questions"], list):
        raise ValueError("Invalid quiz format: 'questions' list missing.")

    # Ensure option IDs and fields are clean
    valid_options = {"A", "B", "C", "D"}
    for idx, q in enumerate(quiz_data["questions"], 1):
        q["id"] = idx
        if "options" not in q or len(q["options"]) < 4:
            raise ValueError(f"Question {idx} does not have 4 options.")
        if q.get("correct_option") not in valid_options:
            q["correct_option"] = "A"
        if not q.get("citation"):
            q["citation"] = f"{document_name} @ Reference snippet"

    quiz_data["document_name"] = document_name
    quiz_data["difficulty"] = diff
    quiz_data["total_questions"] = len(quiz_data["questions"])

    return quiz_data
