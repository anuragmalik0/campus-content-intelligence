"""
Azure AI Speech Service Integration
Supports Text-to-Speech (TTS - Audio Read Aloud) and Speech-to-Text (STT - Voice Input)
using Azure Cognitive Services Speech REST APIs.
"""

import os
import re
import html
import requests
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

def get_speech_config() -> Tuple[str, str]:
    """Dynamically reload and return current Azure Speech credentials."""
    load_dotenv(override=True)
    key = os.getenv("AZURE_SPEECH_KEY", "").strip()
    region = os.getenv("AZURE_SPEECH_REGION", "eastus2").strip()
    return key, region


def is_speech_configured() -> bool:
    """Check if Azure Speech service credentials are provided."""
    key, region = get_speech_config()
    return bool(key and region and "<your-" not in key)



def clean_text_for_speech(text: str) -> str:
    """Remove markdown artifacts, URLs, and code blocks before feeding into speech synthesizer."""
    if not text:
        return ""
    # Strip citation brackets like [filename @ snippet] or [Source @ 1]
    t = re.sub(r'\[.*?@.*?\]', '', text)
    # Strip markdown links [label](url) -> label
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    # Strip markdown bold/italic
    t = re.sub(r'[*_#`]', '', t)
    # Collapse multiple spaces and newlines
    t = re.sub(r'\s+', ' ', t).strip()
    return html.escape(t)


def synthesize_speech(text: str, voice_name: str = "en-US-JennyNeural") -> Tuple[bool, bytes, str]:
    """
    Synthesize text into MP3 audio using Azure AI Speech REST API.
    Returns: (success: bool, audio_bytes: bytes, error_or_mime: str)
    """
    if not is_speech_configured():
        return False, b"", "Azure Speech not configured in .env (AZURE_SPEECH_KEY or AZURE_SPEECH_REGION missing)."

    clean_content = clean_text_for_speech(text)
    if not clean_content:
        return False, b"", "Text is empty after preprocessing."

    # Cap text length to avoid timeouts
    if len(clean_content) > 2000:
        clean_content = clean_content[:2000] + "..."

    speech_key, speech_region = get_speech_config()
    tts_url = f"https://{speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": speech_key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
        "User-Agent": "CampusContentIntelligenceAgent"
    }

    ssml = (
        f"<speak version='1.0' xml:lang='en-US'>"
        f"<voice xml:lang='en-US' name='{voice_name}'>"
        f"{clean_content}"
        f"</voice>"
        f"</speak>"
    )

    try:
        response = requests.post(tts_url, headers=headers, data=ssml.encode("utf-8"), timeout=15)
        if response.status_code == 200 and response.content:
            return True, response.content, "audio/mpeg"
        else:
            err_msg = f"Azure Speech API returned status {response.status_code}: {response.text[:200]}"
            print(f"[WARN] {err_msg}")
            return False, b"", err_msg
    except Exception as e:
        print(f"[ERROR] Azure Speech synthesis failed: {e}")
        return False, b"", str(e)


def transcribe_audio(audio_data: bytes, content_type: str = "audio/wav") -> Tuple[bool, str]:
    """
    Transcribes audio bytes to text using Azure AI Speech STT REST API.
    Returns: (success: bool, transcript: str)
    """
    if not is_speech_configured():
        return False, "Azure Speech not configured in .env."

    speech_key, speech_region = get_speech_config()
    stt_url = f"https://{speech_region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=en-US"
    headers = {
        "Ocp-Apim-Subscription-Key": speech_key,
        "Content-Type": content_type,
        "Accept": "application/json"
    }

    try:
        response = requests.post(stt_url, headers=headers, data=audio_data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            status = result.get("RecognitionStatus")
            if status == "Success":
                return True, result.get("DisplayText", "")
            else:
                return False, f"Speech recognition status: {status}"
        else:
            return False, f"Azure STT failed with status {response.status_code}: {response.text[:150]}"
    except Exception as e:
        return False, f"Error calling Azure Speech STT: {e}"
