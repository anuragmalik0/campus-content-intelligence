"""
Azure Authentication Smoke Test
Phase 0 Exit Criteria Verification

Tests that:
1. Environment variables load correctly from .env (without logging secret values)
2. Azure AI Search credentials authenticate successfully
3. Azure OpenAI / Foundry credentials authenticate successfully
4. Azure AI Content Understanding credentials authenticate successfully
"""

import os
import sys
from dotenv import load_dotenv

def mask_credential(val: str) -> str:
    """Safely show only the last 4 chars for confirmation, never the full key."""
    if not val or len(val) < 8:
        return "********"
    return f"...{val[-4:]}"

def test_auth():
    print("========================================")
    print("  Phase 0: Azure Authentication Test")
    print("========================================")
    
    # Check .env existence
    if not os.path.exists(".env"):
        print("[!] .env file not found.")
        print("    Please copy .env.example to .env and fill in your Azure credentials.")
        return False

    load_dotenv()

    # Load configuration
    content_endpoint = os.getenv("CONTENT_UNDERSTANDING_ENDPOINT", "").strip()
    content_key = os.getenv("CONTENT_UNDERSTANDING_KEY", "").strip()

    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").strip()
    search_key = os.getenv("AZURE_SEARCH_KEY", "").strip()
    search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "campus-content-index").strip()

    foundry_endpoint = os.getenv("FOUNDRY_ENDPOINT", "").strip()
    foundry_key = os.getenv("FOUNDRY_API_KEY", "").strip()
    foundry_deployment = os.getenv("FOUNDRY_MODEL_DEPLOYMENT", "gpt-4o-mini").strip()

    all_present = True
    for name, val in [
        ("CONTENT_UNDERSTANDING_ENDPOINT", content_endpoint),
        ("CONTENT_UNDERSTANDING_KEY", content_key),
        ("AZURE_SEARCH_ENDPOINT", search_endpoint),
        ("AZURE_SEARCH_KEY", search_key),
        ("FOUNDRY_ENDPOINT", foundry_endpoint),
        ("FOUNDRY_API_KEY", foundry_key),
    ]:
        if not val or "<your-" in val or "your-key-here" in val:
            print(f"[-] Missing or placeholder value for: {name}")
            all_present = False
        else:
            print(f"[+] Loaded {name}: {mask_credential(val)}")

    if not all_present:
        print("\n[!] Please update .env with valid credentials before running auth tests.")
        return False

    print("\n--- Verifying Azure AI Search ---")
    search_ok = False
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents.indexes import SearchIndexClient

        search_client = SearchIndexClient(
            endpoint=search_endpoint,
            credential=AzureKeyCredential(search_key)
        )
        # Attempt to list indexes to verify credential authorization
        indexes = list(search_client.list_index_names())
        print(f"[SUCCESS] Connected to Azure AI Search. Found {len(indexes)} existing index(es).")
        search_ok = True
    except Exception as e:
        print(f"[FAILED] Azure AI Search auth error: {type(e).__name__}: {str(e)[:150]}")

    print("\n--- Verifying Azure OpenAI / Microsoft Foundry ---")
    foundry_ok = False
    try:
        from openai import AzureOpenAI

        # Use AzureOpenAI client with key auth
        client = AzureOpenAI(
            azure_endpoint=foundry_endpoint,
            api_key=foundry_key,
            api_version="2024-02-01"
        )
        # Trivial models check
        models = client.models.list()
        print(f"[SUCCESS] Connected to Azure OpenAI / Foundry. Available models checked.")
        foundry_ok = True
    except Exception as e:
        print(f"[FAILED] Azure OpenAI auth error: {type(e).__name__}: {str(e)[:150]}")

    print("\n--- Verifying Azure AI Content Understanding ---")
    content_ok = False
    try:
        import requests
        # Simple ping/GET to check if endpoint recognizes the key
        url = content_endpoint.rstrip("/") + "/contentunderstanding/analyzers?api-version=2024-12-01-preview"
        headers = {
            "Ocp-Apim-Subscription-Key": content_key
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code in [200, 201, 204]:
            print(f"[SUCCESS] Connected to Azure AI Content Understanding (HTTP {resp.status_code}).")
            content_ok = True
        elif resp.status_code in [401, 403]:
            print(f"[FAILED] Azure AI Content Understanding unauthorized (HTTP {resp.status_code}). Check your key.")
        else:
            print(f"[INFO] Azure AI Content Understanding responded with HTTP {resp.status_code}.")
            content_ok = resp.status_code < 500
    except Exception as e:
        print(f"[FAILED] Azure AI Content Understanding connection error: {type(e).__name__}: {str(e)[:150]}")

    print("\n========================================")
    if search_ok and foundry_ok and content_ok:
        print("ALL AUTHENTICATION CHECKS PASSED (Phase 0 Exit Criterion met).")
        return True
    else:
        print("SOME CHECKS FAILED OR WERE INCOMPLETE.")
        return False

if __name__ == "__main__":
    success = test_auth()
    sys.exit(0 if success else 1)
