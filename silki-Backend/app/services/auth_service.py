from fastapi import HTTPException, status

from app.core.security import create_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def register(self, data: RegisterRequest) -> User:
        if await self.repo.get_by_username(data.username):
            raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
        if await self.repo.get_by_username_or_email(data.email):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

        return await self.repo.create(
            username=data.username,
            email=data.email,
            hashed_password=hash_password(data.password),
        )

    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self.repo.get_by_username(data.username)
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
        return self._issue_tokens(user.id)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        from app.core.security import decode_token

        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

        user = await self.repo.get_by_id(payload["sub"])
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
        return self._issue_tokens(user.id)

    @staticmethod
    def _issue_tokens(user_id: str) -> TokenResponse:
        return TokenResponse(
            access_token=create_token(user_id, "access"),
            refresh_token=create_token(user_id, "refresh"),
        )
