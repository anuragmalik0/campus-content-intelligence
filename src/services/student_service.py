"""
Student Profile & Progress Persistence Service
Layer 1 — Cloud Storage Account (Azure Blob & Local Simulator Fallback)

Manages student authentication profiles, course progression, quiz scores,
and inquiry statistics within a dedicated Azure Blob container ('campus-students').
"""

import os
import json
import re
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

# Local fallback directory for offline development
LOCAL_STUDENT_DIR = PROJECT_ROOT / "data" / "student_profiles"
LOCAL_STUDENT_DIR.mkdir(parents=True, exist_ok=True)

CONTAINER_NAME = os.getenv("AZURE_STORAGE_STUDENT_CONTAINER", "campus-students").strip()

from src.services.blob_storage_service import (
    get_blob_storage_config,
    is_blob_storage_configured,
    get_blob_service_client,
    ensure_container_exists
)


def _safe_id(student_id: str) -> str:
    """Sanitize student ID for file and blob path safety."""
    cleaned = re.sub(r'[^a-zA-Z0-9_-]', '_', student_id.strip())
    return cleaned or "default_student"


def _blob_path_for_student(student_id: str) -> str:
    return f"profiles/student_{_safe_id(student_id)}.json"


def get_student_profile(student_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves student profile from local cache or Azure Blob Storage."""
    safe_id = _safe_id(student_id)
    blob_name = _blob_path_for_student(safe_id)

    # 1. Fast path: check local cache first for sub-millisecond response
    local_path = LOCAL_STUDENT_DIR / f"student_{safe_id}.json"
    if local_path.is_file():
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Error reading local student profile: {e}")

    # 2. Check Azure Blob Storage if not in local cache
    if is_blob_storage_configured():
        try:
            client = get_blob_service_client()
            container_client = client.get_container_client(CONTAINER_NAME)
            if container_client.exists():
                blob_client = container_client.get_blob_client(blob_name)
                if blob_client.exists():
                    data_bytes = blob_client.download_blob().readall()
                    profile = json.loads(data_bytes.decode("utf-8"))
                    # Cache locally
                    try:
                        with open(local_path, "w", encoding="utf-8") as f:
                            f.write(json.dumps(profile, indent=2))
                    except Exception:
                        pass
                    return profile
        except Exception as e:
            print(f"[WARN] Error reading student profile from Azure Blob: {e}")

    return None


def save_student_profile(profile: Dict[str, Any]) -> bool:
    """Saves student profile JSON to Azure Blob Storage (and local fallback)."""
    student_id = profile.get("student_id", "default_student")
    safe_id = _safe_id(student_id)
    blob_name = _blob_path_for_student(safe_id)
    data_str = json.dumps(profile, indent=2)
    saved = False

    # 1. Always persist to local cache immediately
    try:
        local_path = LOCAL_STUDENT_DIR / f"student_{safe_id}.json"
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(data_str)
        saved = True
    except Exception as e:
        print(f"[WARN] Error saving local student profile: {e}")

    # 2. Persist to Azure Blob Storage
    if is_blob_storage_configured():
        try:
            client = get_blob_service_client()
            container_client = ensure_container_exists(client, CONTAINER_NAME)
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(
                data_str.encode("utf-8"),
                overwrite=True
            )
            saved = True
            print(f"[AZURE BLOB] Saved student profile '{safe_id}' to container '{CONTAINER_NAME}'.")
        except Exception as e:
            print(f"[WARN] Error saving student profile to Azure Blob: {e}")

    return saved


def get_or_create_student(
    student_id: str,
    name: str,
    department: str = "Computer Science & Engineering",
    email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieves an existing student profile or initializes a fresh one,
    updating the last_login timestamp in Azure Blob Storage.
    """
    safe_id = _safe_id(student_id)
    existing = get_student_profile(safe_id)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if existing:
        existing["last_login"] = now_iso
        if name and name.strip():
            existing["name"] = name.strip()
        if department and department.strip():
            existing["department"] = department.strip()
        if email and email.strip():
            existing["email"] = email.strip()
        # Ensure mandatory keys are always populated
        if not existing.get("department"):
            existing["department"] = department.strip() if department else "Computer Science & Engineering"
        if not existing.get("name"):
            existing["name"] = name.strip() if name else f"Student {safe_id}"
        if "stats" not in existing:
            existing["stats"] = {
                "quizzes_taken": 0,
                "quizzes_passed": 0,
                "total_score": 0,
                "total_possible": 0,
                "average_score_pct": 0.0,
                "questions_asked": 0
            }
        save_student_profile(existing)
        return existing

    # Create new profile
    new_profile: Dict[str, Any] = {
        "student_id": student_id.strip(),
        "name": name.strip() or f"Student {safe_id}",
        "department": department.strip() or "Computer Science & Engineering",
        "email": (email or f"{safe_id.lower()}@campus.edu").strip(),
        "created_at": now_iso,
        "last_login": now_iso,
        "storage_provider": "Azure Blob Storage" if is_blob_storage_configured() else "Local Storage Simulator",
        "stats": {
            "quizzes_taken": 0,
            "quizzes_passed": 0,
            "total_score": 0,
            "total_possible": 0,
            "average_score_pct": 0.0,
            "questions_asked": 0
        },
        "quiz_history": [],
        "recent_queries": []
    }

    save_student_profile(new_profile)
    return new_profile


def record_quiz_progress(student_id: str, quiz_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Appends a completed quiz record to the student's cloud profile
    and recalculates aggregated performance statistics.
    """
    profile = get_student_profile(student_id)
    if not profile:
        profile = get_or_create_student(student_id, name=f"Student {_safe_id(student_id)}")

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    score = int(quiz_record.get("score", 0))
    total = int(quiz_record.get("total", 1))
    pct = round((score / max(1, total)) * 100, 1)

    record_entry = {
        "quiz_id": quiz_record.get("quiz_id") or f"quiz-{int(datetime.datetime.now().timestamp())}",
        "document_name": quiz_record.get("document_name", "Academic Document"),
        "topic": quiz_record.get("topic") or "General Assessment",
        "difficulty": quiz_record.get("difficulty", "medium"),
        "score": score,
        "total": total,
        "percentage": pct,
        "passed": pct >= 60.0,
        "completed_at": now_iso
    }

    history = profile.setdefault("quiz_history", [])
    history.insert(0, record_entry)
    profile["quiz_history"] = history[:50]  # retain last 50 quizzes

    # Update aggregate stats
    stats = profile.setdefault("stats", {})
    stats["quizzes_taken"] = stats.get("quizzes_taken", 0) + 1
    if pct >= 60.0:
        stats["quizzes_passed"] = stats.get("quizzes_passed", 0) + 1

    stats["total_score"] = stats.get("total_score", 0) + score
    stats["total_possible"] = stats.get("total_possible", 0) + total

    tot_score = stats["total_score"]
    tot_poss = stats["total_possible"]
    stats["average_score_pct"] = round((tot_score / max(1, tot_poss)) * 100, 1)

    profile["last_active"] = now_iso
    save_student_profile(profile)
    return profile


def record_question_asked(student_id: str, question: str) -> Dict[str, Any]:
    """Records a question inquiry to the student's cloud learning log."""
    profile = get_student_profile(student_id)
    if not profile:
        profile = get_or_create_student(student_id, name=f"Student {_safe_id(student_id)}")

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    stats = profile.setdefault("stats", {})
    stats["questions_asked"] = stats.get("questions_asked", 0) + 1

    queries = profile.setdefault("recent_queries", [])
    queries.insert(0, {
        "question": question.strip(),
        "timestamp": now_iso
    })
    profile["recent_queries"] = queries[:30]  # retain last 30 queries
    profile["last_active"] = now_iso

    save_student_profile(profile)
    return profile


def list_all_students() -> List[Dict[str, Any]]:
    """Lists summary cards of all students registered in the system."""
    summaries = []
    seen = set()

    # Search Azure Blob
    if is_blob_storage_configured():
        try:
            client = get_blob_service_client()
            container_client = client.get_container_client(CONTAINER_NAME)
            if container_client.exists():
                for b in container_client.list_blobs(name_starts_with="profiles/"):
                    blob_client = container_client.get_blob_client(b.name)
                    data = json.loads(blob_client.download_blob().readall().decode("utf-8"))
                    sid = data.get("student_id")
                    if sid and sid not in seen:
                        seen.add(sid)
                        summaries.append({
                            "student_id": sid,
                            "name": data.get("name"),
                            "department": data.get("department"),
                            "quizzes_taken": data.get("stats", {}).get("quizzes_taken", 0),
                            "average_score_pct": data.get("stats", {}).get("average_score_pct", 0.0),
                            "last_login": data.get("last_login")
                        })
        except Exception as e:
            print(f"[WARN] Error listing students from Azure Blob: {e}")

    # Fallback to local files
    if LOCAL_STUDENT_DIR.is_dir():
        for f in LOCAL_STUDENT_DIR.glob("student_*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fl:
                    data = json.load(fl)
                    sid = data.get("student_id")
                    if sid and sid not in seen:
                        seen.add(sid)
                        summaries.append({
                            "student_id": sid,
                            "name": data.get("name"),
                            "department": data.get("department"),
                            "quizzes_taken": data.get("stats", {}).get("quizzes_taken", 0),
                            "average_score_pct": data.get("stats", {}).get("average_score_pct", 0.0),
                            "last_login": data.get("last_login")
                        })
            except Exception:
                pass

    return summaries
