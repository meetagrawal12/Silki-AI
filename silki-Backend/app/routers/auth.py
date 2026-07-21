from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user, get_user_repo
from app.db.database import get_db
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserPublic,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])
settings = get_settings()


@router.post("/register", response_model=UserPublic, status_code=201)
@limiter.limit(settings.rate_limit_auth)
async def register(request: Request, data: RegisterRequest, repo: UserRepository = Depends(get_user_repo)):
    user = await AuthService(repo).register(data)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_auth)
async def login(request: Request, data: LoginRequest, repo: UserRepository = Depends(get_user_repo)):
    return await AuthService(repo).login(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, repo: UserRepository = Depends(get_user_repo)):
    return await AuthService(repo).refresh(data.refresh_token)


@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
