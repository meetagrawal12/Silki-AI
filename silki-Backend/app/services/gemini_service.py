"""Gemini chat + vision service — mirrors your existing service pattern."""
import base64
import logging

import httpx

from app.core.config import get_settings

log = logging.getLogger("silki.gemini")
settings = get_settings()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

DEFAULT_MODEL = "gemini-2.5-flash-lite"
DEFAULT_VISION_MODEL = "gemini-2.5-flash"


class GeminiError(RuntimeError):
    pass


async def gemini_chat(prompt: str, model: str = DEFAULT_MODEL) -> str:
    if not settings.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    url = GEMINI_URL.format(model=model)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {
        "x-goog-api-key": settings.gemini_api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            log.error("Gemini API error: %s — %s", e.response.status_code, e.response.text)
            raise GeminiError(f"Gemini API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            log.error("Gemini request failed: %s", e)
            raise GeminiError("Could not reach Gemini API") from e

        data = resp.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        log.warning("Gemini returned unexpected payload shape: %s", data)
        raise GeminiError("Gemini returned no usable response")


async def gemini_vision(
    prompt: str,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    model: str = DEFAULT_VISION_MODEL,
) -> str:
    if not settings.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    url = GEMINI_URL.format(model=model)
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_type, "data": b64_image}},
            ]
        }]
    }
    headers = {
        "x-goog-api-key": settings.gemini_api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            log.error("Gemini vision error: %s — %s", e.response.status_code, e.response.text)
            raise GeminiError(f"Gemini vision error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            log.error("Gemini vision request failed: %s", e)
            raise GeminiError("Could not reach Gemini API") from e

        data = resp.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        log.warning("Gemini vision returned unexpected payload shape: %s", data)
        raise GeminiError("Gemini vision returned no usable response")