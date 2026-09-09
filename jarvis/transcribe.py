"""Speech to text for voice notes.

Anthropic's API doesn't do transcription, so this talks to any OpenAI-compatible
``/audio/transcriptions`` endpoint. That covers OpenAI, Groq (fast and cheap),
and a local whisper.cpp or faster-whisper server if you'd rather no audio left
your machine. Point JARVIS_STT_BASE_URL wherever you like; the only thing that
changes between them is the URL, the key and the model name.
"""

import os

import requests

BASE_URL = os.getenv("JARVIS_STT_BASE_URL", "https://api.openai.com/v1").rstrip("/")
API_KEY = os.getenv("JARVIS_STT_API_KEY", "")
MODEL = os.getenv("JARVIS_STT_MODEL", "whisper-1")
TIMEOUT = 120


class TranscriptionUnavailable(Exception):
    """No transcription backend is configured."""


def available() -> bool:
    # A local server needs no key, so a non-default base URL counts as configured.
    return bool(API_KEY) or "api.openai.com" not in BASE_URL


def transcribe(audio: bytes, filename: str = "voice.ogg") -> str:
    """Transcribe audio bytes to text. Raises TranscriptionUnavailable if no
    backend is set up."""
    if not available():
        raise TranscriptionUnavailable(
            "No transcription backend configured. Set JARVIS_STT_API_KEY (and "
            "optionally JARVIS_STT_BASE_URL) in .env - SETUP.md step 7."
        )
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    response = requests.post(
        f"{BASE_URL}/audio/transcriptions",
        headers=headers,
        files={"file": (filename, audio)},
        data={"model": MODEL},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("text", "").strip()
