"""
LLM orchestration over Groq's free-tier models.
"""
import logging
from dataclasses import dataclass
from typing import AsyncGenerator, List

from fastapi import HTTPException
from groq import AsyncGroq

from app.core.config import get_settings

log = logging.getLogger("silki.llm")
settings = get_settings()

_client = AsyncGroq(api_key=settings.groq_api_key)


@dataclass
class LLMResult:
    content: str
    model_used: str


class LLMService:
    def __init__(self, preferred_model: str | None = None):
        models = settings.groq_models
        if preferred_model and preferred_model in models:
            self.model_order: List[str] = [preferred_model] + [
                m for m in models if m != preferred_model
            ]
        else:
            self.model_order = list(models)

    async def complete(
        self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024
    ) -> LLMResult:
        """Non-streaming completion with automatic fallback across models."""
        last_error: Exception | None = None
        for model in self.model_order:
            try:
                resp = await _client.chat.completions.create(
                    model=model, messages=messages,
                    max_tokens=max_tokens, temperature=temperature,
                )
                content = resp.choices[0].message.content
                if not content or not content.strip():
                    raise ValueError("Empty response from model")
                return LLMResult(content=content, model_used=model)
            except Exception as e:
                last_error = e
                log.warning("Model %s failed: %s", model, e)
                continue

        raise HTTPException(
            502, f"All models failed. Last error: {last_error}"
        )

    async def stream(
        self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Yields (token, model_used) pairs."""
        last_error: Exception | None = None
        for model in self.model_order:
            started = False
            try:
                stream = await _client.chat.completions.create(
                    model=model, messages=messages,
                    max_tokens=max_tokens, temperature=temperature, stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        started = True
                        yield delta, model
                if started:
                    return
                raise ValueError("Model produced no output")
            except Exception as e:
                last_error = e
                log.warning("Streaming model %s failed: %s", model, e)
                if started:
                    return
                continue

        raise HTTPException(502, f"All models failed. Last error: {last_error}")


async def groq_chat(prompt: str, model: str = "") -> str:
    """Helper function exposed for the router."""
    messages = [{"role": "user", "content": prompt}]
    service = LLMService(preferred_model=model if model else None)
    result = await service.complete(messages=messages)
    return result.content   