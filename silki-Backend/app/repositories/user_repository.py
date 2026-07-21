from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Encapsulates every raw query against the users table. Services call
    this instead of writing SQLAlchemy queries directly, so the query logic
    has one home and is easy to swap or optimize later."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return await self.db.get(User, user_id)

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_username_or_email(self, identifier: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(or_(User.username == identifier, User.email == identifier))
        )
        return result.scalar_one_or_none()

    async def create(self, username: str, email: str, hashed_password: str) -> User:
        user = User(username=username, email=email, hashed_password=hashed_password)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
