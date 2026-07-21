"""OpenRouter — access to multiple free-tier models via one API."""
import logging

import httpx

from app.core.config import get_settings

log = logging.getLogger("silki.openrouter")
settings = get_settings()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"


class OpenRouterError(RuntimeError):
    pass


async def openrouter_chat(prompt: str, model: str = DEFAULT_MODEL) -> str:
    if not settings.openrouter_api_key:
        raise OpenRouterError("OPENROUTER_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            log.error("OpenRouter error: %s — %s", e.response.status_code, e.response.text)
            raise OpenRouterError(f"OpenRouter error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise OpenRouterError("Could not reach OpenRouter API") from e

        data = resp.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise OpenRouterError("OpenRouter returned no usable response")