import time

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()
_start_time = time.time()


@router.get("/")
def root():
    return {
        "status": "running",
        "app": settings.app_name,
        "environment": settings.environment,
        "uptime_seconds": int(time.time() - _start_time),
        "docs": "/docs",
    }


@router.get("/health")
def health():
    return {
        "status": "ok",
        "groq_ready": bool(settings.groq_api_key),
        "hf_ready": bool(settings.hf_token),
    }


@router.get("/models")
def list_models():
    return {"available": settings.groq_models}
