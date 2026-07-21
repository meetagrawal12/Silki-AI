from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_chat_repo, get_current_user
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import SessionDetailOut, SessionOut, SessionUpdateRequest

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=List[SessionOut])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    repo: ChatRepository = Depends(get_chat_repo),
):
    return await repo.list_sessions(current_user.id)


@router.get("/{session_id}", response_model=SessionDetailOut)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    repo: ChatRepository = Depends(get_chat_repo),
):
    session = await repo.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@router.patch("/{session_id}", response_model=SessionOut)
async def update_session(
    session_id: str,
    data: SessionUpdateRequest,
    current_user: User = Depends(get_current_user),
    repo: ChatRepository = Depends(get_chat_repo),
):
    session = await repo.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(404, "Session not found")
    return await repo.update_session(session, title=data.title, system_prompt=data.system_prompt)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    repo: ChatRepository = Depends(get_chat_repo),
):
    session = await repo.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(404, "Session not found")
    await repo.delete_session(session)
