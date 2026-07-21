"""Routes a chat request to the correct provider based on `model` field."""
from app.services.gemini_service import gemini_chat
from app.services.openrouter_service import openrouter_chat
from app.services.llm_service import groq_chat

PROVIDER_MAP = {
    "groq": groq_chat,
    "gemini": gemini_chat,
    "openrouter": openrouter_chat,
}


async def route_chat(prompt: str, provider: str = "groq", model: str = "") -> str:
    fn = PROVIDER_MAP.get(provider)
    if fn is None:
        raise ValueError(f"Unknown provider '{provider}'. Choose from: {list(PROVIDER_MAP)}")
    return await (fn(prompt, model) if model else fn(prompt))