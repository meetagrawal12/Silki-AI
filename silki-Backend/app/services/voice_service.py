import logging

from fastapi import HTTPException
from huggingface_hub import InferenceClient

from app.core.config import get_settings

log = logging.getLogger("silki.voice")
settings = get_settings()

# Try providers in order — if hf-inference deprecates this model too,
# fall back automatically instead of hard-failing (see image_service.py).
_PROVIDERS = ["hf-inference", "fal-ai"]


class VoiceService:
    @staticmethod
    async def transcribe(audio_bytes: bytes) -> str:
        """Transcribe audio bytes (webm/wav/mp3) to text via HF's
        automatic-speech-recognition inference API."""
        last_error = None
        for provider in _PROVIDERS:
            try:
                client = InferenceClient(provider=provider, token=settings.hf_token)
                result = client.automatic_speech_recognition(audio_bytes, model=settings.hf_asr_model)
                text = result.text if hasattr(result, "text") else str(result)
                return text.strip()
            except Exception as e:
                log.warning("Transcription via %s failed: %s", provider, e)
                last_error = e
                continue

        log.error("Transcription failed on all providers: %s", last_error)
        raise HTTPException(502, f"Transcription failed: {last_error}")