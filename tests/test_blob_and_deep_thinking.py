import os
import sys
from pathlib import Path

# Add project root
root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "OneDrive" / "Desktop" / "AI-103"
if not root.exists():
    root = Path(r"c:\Users\anura\OneDrive\Desktop\AI-103")
sys.path.insert(0, str(root))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print(f"Project root: {root}")

from src.services.blob_storage_service import (
    upload_document_to_blob,
    list_documents_in_blob,
    get_blob_url,
    is_blob_storage_configured
)
from src.agent.orchestrator import answer_question, build_context_block
from fastapi.testclient import TestClient
from src.ui.server import app

client = TestClient(app)

print("\n--- 1. Testing Blob Storage Service ---")
sample_content = b"Sample lecture notes on optimization dynamics and momentum in neural networks."
filename = "test_deep_thinking_blob.txt"
blob_info = upload_document_to_blob(sample_content, filename, content_type="text/plain")
print(f"Uploaded blob: {blob_info}")
assert blob_info["blob_name"] == filename
assert "blob_url" in blob_info

blobs = list_documents_in_blob()
print(f"Total blobs in storage: {len(blobs)}")
matching_blobs = [b for b in blobs if b["filename"] == filename]
assert len(matching_blobs) > 0, "Uploaded blob not found in list"

url = get_blob_url(filename)
print(f"Blob URL: {url}")
assert len(url) > 0

print("\n--- 2. Testing Server Endpoints ---")
# /api/info
info_res = client.get("/api/info")
assert info_res.status_code == 200
info_data = info_res.json()
print(f"/api/info: {info_data.get('course')} | Blob Configured: {info_data.get('blob_storage_configured')}")
assert "blob_storage_configured" in info_data

# /api/blobs
blobs_res = client.get("/api/blobs")
assert blobs_res.status_code == 200
blobs_data = blobs_res.json()
print(f"/api/blobs returned {len(blobs_data.get('blobs', []))} blobs")

# /api/uploaded-files
files_res = client.get("/api/uploaded-files")
assert files_res.status_code == 200
files_data = files_res.json()
print(f"/api/uploaded-files returned {len(files_data.get('files', []))} files")

print("\n--- 3. Testing RAG Deep Thinking Synthesis (/api/ask) ---")
ask_res = client.post("/api/ask", json={"question": "What is the update rule for gradient descent?"})
assert ask_res.status_code == 200
ask_data = ask_res.json()
print(f"Answered: {ask_data.get('answered')}")
print(f"Thinking Summary:\n{ask_data.get('thinking_summary')}")
print(f"Answer Preview: {ask_data.get('text')[:180]}...")
print(f"Citations count: {len(ask_data.get('citations', []))}")
for c in ask_data.get('citations', []):
    print(f"  - {c.get('source_name')} @ {c.get('location')} | Blob: {c.get('blob_url')}")

assert ask_data.get("answered") is True
assert ask_data.get("thinking_summary") is not None
if ask_data.get("citations"):
    assert "blob_url" in ask_data["citations"][0]

print("\n--- ALL VERIFICATIONS PASSED SUCCESSFULLY! ---")
