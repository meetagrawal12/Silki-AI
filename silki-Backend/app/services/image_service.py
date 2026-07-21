import base64
import logging
import urllib.parse
from io import BytesIO

import httpx
from fastapi import HTTPException
from huggingface_hub import InferenceClient

from app.core.config import get_settings

log = logging.getLogger("silki.image")
settings = get_settings()

# Pollinations.ai is a genuinely free, no-key, no-billing image API — good
# primary choice since HF's paid Inference Providers (nscale/fal-ai/together)
# bill against monthly credits that run out fast, and hf-inference no longer
# serves FLUX.1-schnell at all (deprecated 2026-07-15).
_POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

# HF providers kept as fallback for when Pollinations is rate-limited/down,
# or once you have paid HF credits again.
_HF_PROVIDERS = ["nscale", "fal-ai", "together", "hf-inference"]


class ImageService:
    @staticmethod
    async def _generate_pollinations(prompt: str) -> str:
        url = f"{_POLLINATIONS_BASE}/{urllib.parse.quote(prompt)}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url, params={"nologo": "true"})
            resp.raise_for_status()
            return base64.b64encode(resp.content).decode("utf-8")

    @staticmethod
    def _generate_hf(prompt: str, provider: str) -> str:
        client = InferenceClient(provider=provider, token=settings.hf_token)
        result = client.text_to_image(prompt, model=settings.hf_image_model)

        buf = BytesIO()
        if isinstance(result, bytes):
            buf.write(result)
        else:
            result.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    @staticmethod
    async def generate(prompt: str) -> str:
        """Returns a base64-encoded PNG. Tries Pollinations first (free,
        no billing), then falls back through HF providers."""
        errors: dict[str, str] = {}

        # 1. Free, unmetered — try first.
        try:
            image_b64 = await ImageService._generate_pollinations(prompt)
            log.info("Image generated successfully via pollinations")
            return image_b64
        except Exception as e:
            errors["pollinations"] = str(e)
            log.warning("Image generation via pollinations failed: %s", e)

        # 2. Fall back to HF providers (billed — only useful if you have
        # paid credits or included quota remaining).
        for provider in _HF_PROVIDERS:
            try:
                image_b64 = ImageService._generate_hf(prompt, provider)
                log.info("Image generated successfully via provider=%s", provider)
                return image_b64
            except Exception as e:
                errors[provider] = str(e)
                log.warning("Image generation via provider=%s failed: %s", provider, e)
                continue

        log.error("Image generation failed on all providers: %s", errors)
        summary = "; ".join(f"{p}: {msg}" for p, msg in errors.items())
        raise HTTPException(
            502,
            f"Image generation failed on all providers (pollinations, {', '.join(_HF_PROVIDERS)}). "
            f"Details — {summary}",
        )