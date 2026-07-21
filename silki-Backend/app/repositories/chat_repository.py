from typing import List, Optional, Sequence

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatSession, Message


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---- Sessions ----
    async def create_session(self, user_id: str, title: str = "New chat") -> ChatSession:
        session = ChatSession(user_id=user_id, title=title)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: str, user_id: str) -> Optional[ChatSession]:
        """Scoped to user_id so one user can never fetch another's session."""
        result = await self.db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(self, user_id: str) -> Sequence[ChatSession]:
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.updated_at))
        )
        return result.scalars().all()

    async def update_session(self, session: ChatSession, **fields) -> ChatSession:
        for key, value in fields.items():
            if value is not None:
                setattr(session, key, value)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def delete_session(self, session: ChatSession) -> None:
        await self.db.delete(session)
        await self.db.commit()

    # ---- Messages ----
    async def add_message(
        self, session_id: str, role: str, content: str, model_used: Optional[str] = None
    ) -> Message:
        message = Message(session_id=session_id, role=role, content=content, model_used=model_used)
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_recent_messages(self, session_id: str, limit: int) -> List[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))
