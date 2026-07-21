import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.deps import get_chat_repo, get_current_user
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import LLMService

router = APIRouter(prefix="/chat", tags=["Chat"])
settings = get_settings()
log = logging.getLogger("silki.chat")


async def _build_context(repo: ChatRepository, session_id: str, system_prompt: str | None):
    history = await repo.get_recent_messages(session_id, settings.max_history_messages)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend({"role": m.role if m.role == "user" else "assistant", "content": m.content} for m in history)
    return messages


async def _resolve_session(repo: ChatRepository, user: User, session_id: str | None, first_message: str):
    if session_id:
        session = await repo.get_session(session_id, user.id)
        if not session:
            raise HTTPException(404, "Session not found")
        return session
    title = first_message[:50]
    return await repo.create_session(user.id, title=title)


@router.post("", response_model=ChatResponse)
@limiter.limit(settings.rate_limit_chat)
async def chat(
    request: Request,
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    repo: ChatRepository = Depends(get_chat_repo),
):
    """Non-streaming chat — simplest integration path for basic clients."""
    session = await _resolve_session(repo, current_user, data.session_id, data.message)
    context = await _build_context(repo, session.id, session.system_prompt)
    context.append({"role": "user", "content": data.message})

    result = await LLMService(preferred_model=data.model).complete(
        context, temperature=data.temperature
    )

    await repo.add_message(session.id, "user", data.message)
    await repo.add_message(session.id, "assistant", result.content, model_used=result.model_used)

    return ChatResponse(session_id=session.id, reply=result.content, model_used=result.model_used)


@router.post("/stream")
@limiter.limit(settings.rate_limit_chat)
async def chat_stream(
    request: Request,
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    repo: ChatRepository = Depends(get_chat_repo),
):
    """Server-Sent Events streaming endpoint. Each event is a JSON payload:
    {"type": "token", "content": "..."} while generating, then a final
    {"type": "done", "session_id": ..., "model_used": ...}."""
    session = await _resolve_session(repo, current_user, data.session_id, data.message)
    context = await _build_context(repo, session.id, session.system_prompt)
    context.append({"role": "user", "content": data.message})

    await repo.add_message(session.id, "user", data.message)

    async def event_generator():
        full_reply = []
        model_used = None
        try:
            async for token, model in LLMService(preferred_model=data.model).stream(
                context, temperature=data.temperature
            ):
                full_reply.append(token)
                model_used = model
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except HTTPException as e:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(e.detail)})}\n\n"
            return

        reply_text = "".join(full_reply)
        if reply_text:
            await repo.add_message(session.id, "assistant", reply_text, model_used=model_used)

        yield f"data: {json.dumps({'type': 'done', 'session_id': session.id, 'model_used': model_used})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
