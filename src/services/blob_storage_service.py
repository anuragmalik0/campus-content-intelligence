"""
Azure Blob Storage Service
Layer 1/2 — Cloud Persistence & Storage Provenance

Manages persistent cloud document storage in Azure Blob Storage.
Provides upload, download, delete, and list operations for academic documents (PDF, DOCX, TXT),
enabling RAG data retrieval with verifiable cloud document provenance.
Includes automatic local persistent fallback for offline execution.
"""

import os
import io
import re
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

# Local fallback directory
LOCAL_BLOB_DIR = PROJECT_ROOT / "data" / "blob_storage"


def get_blob_storage_config() -> Tuple[str, str, str, str]:
    """Dynamically loads Azure Blob Storage credentials from environment."""
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "").strip()
    account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY", "").strip()
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "campus-documents").strip()
    return conn_str, account_name, account_key, container_name


def is_blob_storage_configured() -> bool:
    """Checks whether valid Azure Blob Storage credentials are present."""
    conn_str, account_name, account_key, _ = get_blob_storage_config()
    if conn_str and "<your-" not in conn_str:
        return True
    if account_name and account_key and "<your-" not in account_name and "your-key" not in account_key:
        return True
    return False


def get_blob_service_client():
    """Returns an authenticated Azure BlobServiceClient instance."""
    from azure.storage.blob import BlobServiceClient

    conn_str, account_name, account_key, _ = get_blob_storage_config()
    if conn_str:
        return BlobServiceClient.from_connection_string(conn_str)
    if account_name and account_key:
        account_url = f"https://{account_name}.blob.core.windows.net"
        return BlobServiceClient(account_url=account_url, credential=account_key)
    raise RuntimeError("Azure Blob Storage credentials are not configured in .env.")


def ensure_container_exists(client, container_name: str):
    """Ensures the specified container exists in Azure Blob Storage."""
    container_client = client.get_container_client(container_name)
    if not container_client.exists():
        container_client.create_container()
    return container_client


def get_content_type(filename: str) -> str:
    """Infers appropriate MIME Content-Type from filename extension."""
    ext = Path(filename).suffix.lower()
    types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
        ".csv": "text/csv; charset=utf-8",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    return types.get(ext, "application/octet-stream")


def upload_document_to_blob(
    file_bytes: bytes,
    filename: str,
    content_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Uploads document to Azure Blob Storage (or local persistent simulator).

    Returns:
        Dict with blob_name, blob_url, container_name, storage_provider, file_size, etc.
    """
    safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    mime = content_type or get_content_type(safe_filename)

    # 1. Cloud Azure Blob Storage
    if is_blob_storage_configured():
        try:
            from azure.storage.blob import ContentSettings

            conn_str, account_name, account_key, container_name = get_blob_storage_config()
            client = get_blob_service_client()
            container_client = ensure_container_exists(client, container_name)
            blob_client = container_client.get_blob_client(safe_filename)

            settings = ContentSettings(content_type=mime)
            blob_client.upload_blob(file_bytes, overwrite=True, content_settings=settings)

            blob_url = blob_client.url
            print(f"[AZURE BLOB] Successfully uploaded '{safe_filename}' to container '{container_name}'. URL: {blob_url}")

            return {
                "success": True,
                "blob_name": safe_filename,
                "original_filename": filename,
                "blob_url": blob_url,
                "container_name": container_name,
                "storage_provider": "Azure Blob Storage",
                "file_size": len(file_bytes),
                "content_type": mime,
                "uploaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        except Exception as e:
            print(f"[WARN] Azure Blob Storage upload failed: {e}. Falling back to local persistent store.")

    # 2. Local Fallback Simulator
    LOCAL_BLOB_DIR.mkdir(parents=True, exist_ok=True)
    local_path = LOCAL_BLOB_DIR / safe_filename
    with open(local_path, "wb") as f:
        f.write(file_bytes)

    local_url = f"/api/blobs/file/{safe_filename}"
    return {
        "success": True,
        "blob_name": safe_filename,
        "original_filename": filename,
        "blob_url": local_url,
        "container_name": "local-blob-storage",
        "storage_provider": "Local Blob Simulator",
        "file_size": len(file_bytes),
        "content_type": mime,
        "uploaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }


def download_document_from_blob(filename: str) -> Optional[bytes]:
    """Retrieves raw bytes for a file from Azure Blob Storage (or local simulator)."""
    safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)

    if is_blob_storage_configured():
        try:
            _, _, _, container_name = get_blob_storage_config()
            client = get_blob_service_client()
            blob_client = client.get_container_client(container_name).get_blob_client(safe_filename)
            if blob_client.exists():
                stream = blob_client.download_blob()
                return stream.readall()
        except Exception as e:
            print(f"[WARN] Failed to download '{safe_filename}' from Azure Blob: {e}")

    # Fallback to local
    local_path = LOCAL_BLOB_DIR / safe_filename
    if local_path.is_file():
        return local_path.read_bytes()

    # Check sample_media
    media_path = PROJECT_ROOT / "data" / "sample_media" / filename
    if media_path.is_file():
        return media_path.read_bytes()

    return None


def delete_document_from_blob(filename: str) -> bool:
    """Deletes a file from Azure Blob Storage and local cache."""
    safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    deleted = False

    if is_blob_storage_configured():
        try:
            _, _, _, container_name = get_blob_storage_config()
            client = get_blob_service_client()
            blob_client = client.get_container_client(container_name).get_blob_client(safe_filename)
            if blob_client.exists():
                blob_client.delete_blob()
                deleted = True
                print(f"[AZURE BLOB] Deleted '{safe_filename}' from container '{container_name}'.")
        except Exception as e:
            print(f"[WARN] Error deleting '{safe_filename}' from Azure Blob: {e}")

    local_path = LOCAL_BLOB_DIR / safe_filename
    if local_path.is_file():
        try:
            local_path.unlink()
            deleted = True
        except Exception:
            pass

    return deleted


def list_documents_in_blob() -> List[Dict[str, Any]]:
    """Lists all active files in Azure Blob Storage container (and local simulator)."""
    results: List[Dict[str, Any]] = []
    seen = set()

    if is_blob_storage_configured():
        try:
            _, _, _, container_name = get_blob_storage_config()
            client = get_blob_service_client()
            container_client = client.get_container_client(container_name)
            if container_client.exists():
                for b in container_client.list_blobs():
                    blob_client = container_client.get_blob_client(b.name)
                    results.append({
                        "filename": b.name,
                        "blob_url": blob_client.url,
                        "size": b.size,
                        "content_type": b.content_settings.content_type if b.content_settings else "application/octet-stream",
                        "last_modified": b.last_modified.isoformat() if b.last_modified else None,
                        "storage_provider": "Azure Blob Storage",
                        "container_name": container_name
                    })
                    seen.add(b.name)
        except Exception as e:
            print(f"[WARN] Error listing Azure Blobs: {e}")

    # Merge local blobs
    if LOCAL_BLOB_DIR.is_dir():
        for f in LOCAL_BLOB_DIR.glob("*"):
            if f.is_file() and f.name not in seen and not f.name.startswith("."):
                results.append({
                    "filename": f.name,
                    "blob_url": f"/api/blobs/file/{f.name}",
                    "size": f.stat().st_size,
                    "content_type": get_content_type(f.name),
                    "last_modified": datetime.datetime.fromtimestamp(f.stat().st_mtime, tz=datetime.timezone.utc).isoformat(),
                    "storage_provider": "Local Blob Simulator",
                    "container_name": "local-blob-storage"
                })
                seen.add(f.name)

    return results


def get_blob_url(filename: str) -> str:
    """Returns access URL for a blob."""
    safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    if is_blob_storage_configured():
        try:
            _, _, _, container_name = get_blob_storage_config()
            client = get_blob_service_client()
            blob_client = client.get_container_client(container_name).get_blob_client(safe_filename)
            return blob_client.url
        except Exception:
            pass
    return f"/api/blobs/file/{safe_filename}"
