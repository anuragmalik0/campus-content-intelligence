"""
CampusMind — FastAPI Web Server
Layer 4 — Web Interface & Media Backend
Provides interactive REST APIs and document synchronization backend.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.orchestrator import answer_question
from src.agent.quiz_agent import generate_quiz, analyze_document_knowledge
from src.indexing.search_index import load_cached_chunks_and_index
from src.services.speech_service import synthesize_speech, transcribe_audio, is_speech_configured
from src.services.translator_service import translate_text, is_translator_configured, SUPPORTED_LANGUAGES
from src.services.document_indexer import (
    process_and_index_file,
    delete_document_from_azure_search,
    load_manifest
)
from src.services.blob_storage_service import (
    list_documents_in_blob,
    get_blob_url,
    is_blob_storage_configured,
    LOCAL_BLOB_DIR
)
from src.services.student_service import (
    get_or_create_student,
    get_student_profile,
    record_quiz_progress,
    record_question_asked,
    list_all_students
)

app = FastAPI(
    title="CampusMind API",
    description="Multi-format lecture content retrieval and interactive synchronizer API",
    version="1.0.0"
)

# Enable CORS for local dev flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    """Ensure static files and API responses are never stale in browser cache."""
    response = await call_next(request)
    if request.url.path.endswith((".html", ".js", ".css")) or request.url.path in ("/", "/api/info"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

MEDIA_DIR = PROJECT_ROOT / "data" / "sample_media"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
STATIC_DIR = FRONTEND_DIST if (FRONTEND_DIST / "index.html").is_file() else (Path(__file__).resolve().parent / "static")



class QuestionRequest(BaseModel):
    question: str


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US-JennyNeural"


class STTRequest(BaseModel):
    audio_base64: str
    mime_type: Optional[str] = "audio/wav"


class TranslateRequest(BaseModel):
    text: str
    target_lang: str


class QuizRequest(BaseModel):
    document_name: str
    difficulty: Optional[str] = "medium"
    count: Optional[int] = 5
    topic: Optional[str] = None


class AnalyzeDocRequest(BaseModel):
    document_name: str


class StudentLoginRequest(BaseModel):
    student_id: str
    name: Optional[str] = ""
    department: Optional[str] = "Computer Science & Engineering"
    email: Optional[str] = None


class RecordQuizRequest(BaseModel):
    student_id: str
    document_name: Optional[str] = "Academic Document"
    topic: Optional[str] = "General Assessment"
    difficulty: Optional[str] = "medium"
    score: int
    total: int
    quiz_id: Optional[str] = None


class RecordQueryRequest(BaseModel):
    student_id: str
    question: str


@app.get("/api/info")
def get_info():
    """Return course metadata, indexed sources, and capability status."""
    count = load_cached_chunks_and_index()
    return {
        "course": "AI-103: Deep Learning Foundations",
        "topic": "Gradient Descent & Optimization Dynamics",
        "lecture": "Lecture 3: Convergence Rates, Vanishing Gradients & Momentum",
        "total_chunks": count,
        "model_name": os.getenv("FOUNDRY_MODEL_DEPLOYMENT", "gpt-5-mini"),
        "provider": "Microsoft Azure AI Foundry",
        "blob_storage_configured": is_blob_storage_configured(),
        "speech_available": is_speech_configured(),
        "translator_available": is_translator_configured(),
        "supported_languages": SUPPORTED_LANGUAGES,
        "sources": [
            {
                "name": "neural_networks_notes.pdf",
                "type": "notes",
                "title": "Comprehensive Lecture Notes",
                "badge": "Notes (PDF)",
                "details": "4 Pages — In-depth mathematical formulations & proofs"
            },
            {
                "name": "neural_networks_slides.pdf",
                "type": "slides",
                "title": "Professor's Slide Deck",
                "badge": "Slides (PDF)",
                "details": "6 Slides — High-level diagrams, bullet points, and key definitions"
            }
        ],
        "demo_questions": []
    }


@app.post("/api/ask")
def ask_question_endpoint(req: QuestionRequest):
    """Execute the agent orchestrator seam and return answer with verifiable citations."""
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    result = answer_question(req.question.strip())
    return result


@app.post("/api/speech/tts")
def speech_tts_endpoint(req: TTSRequest):
    """Synthesizes text into audio using Azure AI Speech REST API."""
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    success, audio_bytes, info = synthesize_speech(req.text, req.voice or "en-US-JennyNeural")
    if not success:
        return JSONResponse(
            status_code=503 if not is_speech_configured() else 500,
            content={"success": False, "error": info, "fallback_to_browser": True}
        )

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"}
    )


@app.post("/api/speech/stt")
def speech_stt_endpoint(req: STTRequest):
    """Transcribes base64-encoded audio using Azure AI Speech STT."""
    try:
        audio_bytes = base64.b64decode(req.audio_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 audio: {e}")

    success, result_text = transcribe_audio(audio_bytes, req.mime_type or "audio/wav")
    if not success:
        return JSONResponse(
            status_code=503 if not is_speech_configured() else 500,
            content={"success": False, "error": result_text, "fallback_to_browser": True}
        )

    return {"success": True, "transcript": result_text}


@app.post("/api/translate")
def translate_endpoint(req: TranslateRequest):
    """Translates text to target language using Azure AI Translator."""
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text to translate cannot be empty.")

    success, translated_text = translate_text(req.text, req.target_lang)
    if not success:
        return JSONResponse(
            status_code=503 if not is_translator_configured() else 500,
            content={"success": False, "error": translated_text, "fallback": False}
        )

    return {"success": True, "translated_text": translated_text, "target_lang": req.target_lang}


@app.post("/api/upload")
async def upload_document_endpoint(file: UploadFile = File(...)):
    """
    Accepts user-uploaded documents (PDF, DOCX, TXT, MD), extracts text,
    and indexes chunks directly into the live Azure AI Search cloud index.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    ext = Path(file.filename).suffix.lower()
    allowed = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".json"}
    if ext not in allowed:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported format '{ext}'. Supported: {', '.join(allowed)}"
        )

    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File exceeds maximum size of 20MB.")

        result = process_and_index_file(content, file.filename)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process and index document: {e}")


@app.get("/api/uploaded-files")
def get_uploaded_files_endpoint():
    """Returns the list of active user-uploaded documents indexed in Azure AI Search and Azure Blob Storage."""
    manifest = load_manifest()
    files_list = []
    for fname, meta in manifest.items():
        blob_url = meta.get("blob_url") or get_blob_url(meta.get("blob_name") or fname)
        storage_provider = meta.get("storage_provider") or ("Azure Blob Storage" if is_blob_storage_configured() else "Local Blob Simulator")
        files_list.append({
            "filename": fname,
            "chunk_count": meta.get("chunk_count", 0),
            "preview": meta.get("preview", ""),
            "file_size": meta.get("file_size", 0),
            "blob_url": blob_url,
            "storage_provider": storage_provider
        })
    return {"files": files_list}


@app.get("/api/blobs")
def list_blobs_endpoint():
    """Lists all stored blobs in Azure Blob Storage container and local simulator."""
    return {"blobs": list_documents_in_blob()}


@app.get("/api/blobs/file/{filename}")
def serve_blob_file(filename: str):
    """Serves a stored document from local blob simulator if Azure direct URL is not used."""
    local_path = LOCAL_BLOB_DIR / filename
    if not local_path.is_file():
        raise HTTPException(status_code=404, detail="Blob document not found in storage.")

    content_type = "application/octet-stream"
    if filename.endswith(".pdf"):
        content_type = "application/pdf"
    elif filename.endswith(".txt"):
        content_type = "text/plain; charset=utf-8"
    elif filename.endswith(".docx"):
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif filename.endswith(".json"):
        content_type = "application/json"

    return FileResponse(
        path=local_path,
        media_type=content_type,
        filename=filename
    )


@app.delete("/api/uploaded-files/{filename}")
def delete_uploaded_file_endpoint(filename: str):
    """Deletes all indexed chunks for a file from Azure AI Search."""
    success, msg = delete_document_from_azure_search(filename)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": msg, "filename": filename}


@app.post("/api/quiz/analyze-doc")
def quiz_analyze_doc_endpoint(req: AnalyzeDocRequest):
    """
    Phase 1: Agentic Document Comprehension
    Extracts high-level topics, theoretical concepts, and exercises from the document.
    """
    if not req.document_name or not req.document_name.strip():
        raise HTTPException(status_code=400, detail="Document name is required.")
    try:
        data = analyze_document_knowledge(req.document_name.strip())
        return data
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze document knowledge: {e}")


@app.post("/api/quiz/generate")
def quiz_generate_endpoint(req: QuizRequest):
    """
    Agentic Assessment Endpoint:
    Analyzes document text and generates structured MCQs across difficulty levels.
    """
    if not req.document_name or not req.document_name.strip():
        raise HTTPException(status_code=400, detail="Document name is required.")

    try:
        quiz = generate_quiz(
            document_name=req.document_name.strip(),
            difficulty=req.difficulty or "medium",
            count=req.count or 5,
            topic=req.topic.strip() if req.topic else None
        )
        return quiz
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {e}")


@app.post("/api/quiz/generate-from-file")
async def quiz_generate_from_file_endpoint(
    file: UploadFile = File(...),
    difficulty: str = Form("medium"),
    count: int = Form(5),
    topic: Optional[str] = Form(None)
):
    """
    One-Step Workflow:
    Accepts an uploaded question/notes PDF or document, parses via Azure Document Intelligence,
    indexes into Azure AI Search, and immediately synthesizes an interactive assessment quiz.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        # Index document using Azure AI Document Intelligence
        process_and_index_file(content, file.filename)

        # Generate quiz from the freshly indexed document
        quiz = generate_quiz(
            document_name=file.filename,
            difficulty=difficulty,
            count=count,
            topic=topic.strip() if topic else None
        )
        return quiz
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document assessment generation failed: {e}")


@app.post("/api/student/login")
def student_login_endpoint(req: StudentLoginRequest):
    """
    Authenticates or auto-registers a student profile in Azure Storage Account.
    Returns the student profile, academic department, and accumulated progress stats.
    """
    if not req.student_id or not req.student_id.strip():
        raise HTTPException(status_code=400, detail="Student ID cannot be empty.")

    profile = get_or_create_student(
        student_id=req.student_id.strip(),
        name=req.name.strip() if req.name else "",
        department=req.department.strip() if req.department else "Computer Science & Engineering",
        email=req.email.strip() if req.email else None
    )
    return profile


@app.get("/api/student/profile/{student_id}")
def student_profile_endpoint(student_id: str):
    """Retrieves full student profile, learning history, and stats from Azure Storage."""
    profile = get_student_profile(student_id.strip())
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return profile


@app.post("/api/student/record-quiz")
def student_record_quiz_endpoint(req: RecordQuizRequest):
    """Records a completed quiz into student's cloud storage profile and updates metrics."""
    if not req.student_id or not req.student_id.strip():
        raise HTTPException(status_code=400, detail="Student ID is required.")

    quiz_data = {
        "quiz_id": req.quiz_id,
        "document_name": req.document_name,
        "topic": req.topic,
        "difficulty": req.difficulty,
        "score": req.score,
        "total": req.total
    }
    updated = record_quiz_progress(req.student_id.strip(), quiz_data)
    return {"success": True, "profile": updated}


@app.post("/api/student/record-query")
def student_record_query_endpoint(req: RecordQueryRequest):
    """Records an asked question into student's cloud learning activity log."""
    if not req.student_id or not req.student_id.strip():
        raise HTTPException(status_code=400, detail="Student ID is required.")
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    updated = record_question_asked(req.student_id.strip(), req.question.strip())
    return {"success": True, "profile": updated}


@app.get("/api/student/list")
def student_list_endpoint():
    """Lists registered students across campus departments."""
    students = list_all_students()
    return {"students": students}


@app.get("/media/{filename}")
def serve_media(filename: str, request: Request):
    """Serve media documents (PDF/notes)."""
    media_path = MEDIA_DIR / filename
    if not media_path.is_file():
        raise HTTPException(status_code=404, detail="Media file not found.")
    
    # Determine MIME type
    if filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".txt"):
        media_type = "text/plain; charset=utf-8"
    elif filename.endswith(".json"):
        media_type = "application/json"
    else:
        media_type = "application/octet-stream"
        
    return FileResponse(
        path=media_path,
        media_type=media_type,
        filename=filename
    )


# Mount static assets directory
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("  🚀 CampusMind Web Server")
    print("  🌐 Interface available at: http://localhost:8000")
    print("  📚 API documentation at:   http://localhost:8000/docs")
    print("=" * 60 + "\n")
    uvicorn.run("src.ui.server:app", host="127.0.0.1", port=8000, reload=True)
