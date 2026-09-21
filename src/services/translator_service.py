"""
Azure AI Translator Service Integration
Translates text and assistant responses into multiple languages (Hindi, Spanish, French, German, etc.)
using the Azure Cognitive Services Translator Text API.
"""

import os
import requests
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

def get_translator_config() -> Tuple[str, str, str]:
    """Dynamically reload and return current Azure Translator credentials."""
    load_dotenv(override=True)
    key = os.getenv("AZURE_TRANSLATOR_KEY", "").strip()
    region = os.getenv("AZURE_TRANSLATOR_REGION", os.getenv("AZURE_SPEECH_REGION", "eastus2")).strip()
    endpoint = os.getenv("AZURE_TRANSLATOR_ENDPOINT", "https://api.cognitive.microsofttranslator.com").strip().rstrip("/")
    return key, region, endpoint


def is_translator_configured() -> bool:
    """Check if Azure Translator credentials are provided."""
    key, _, _ = get_translator_config()
    return bool(key and "<your-" not in key)



SUPPORTED_LANGUAGES = {
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "te": "Telugu",
    "ta": "Tamil",
    "zh-Hans": "Chinese (Simplified)",
    "ja": "Japanese",
    "ar": "Arabic",
    "en": "English"
}


def translate_text(text: str, target_lang: str) -> Tuple[bool, str]:
    """
    Translates input text to target language code using Azure AI Translator REST API.
    Returns: (success: bool, translated_text_or_error: str)
    """
    if not text or not text.strip():
        return False, "Text to translate is empty."

    if target_lang == "en":
        return True, text

    # Call Azure Translator API if configured
    if is_translator_configured():
        key, region, endpoint = get_translator_config()
        url = f"{endpoint}/translate?api-version=3.0&to={target_lang}"
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Ocp-Apim-Subscription-Region": region,
            "Content-Type": "application/json"
        }
        body = [{"Text": text}]

        try:
            response = requests.post(url, headers=headers, json=body, timeout=12)
            if response.status_code == 200:
                result = response.json()
                translated = result[0]["translations"][0]["text"]
                return True, translated
            else:
                err_msg = f"Azure Translator API returned status {response.status_code}: {response.text[:150]}"
                print(f"[WARN] {err_msg}")
                return False, err_msg
        except Exception as e:
            print(f"[ERROR] Azure Translator call failed: {e}")
            return False, str(e)

    # If Azure Translator is not yet configured, provide helpful guidance
    return False, "Azure Translator is not configured in .env (AZURE_TRANSLATOR_KEY is missing)."
