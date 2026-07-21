"""
Silki AI — production backend entrypoint.

This file only wires things together: config, database lifecycle, CORS,
rate limiting, exception handling, and routers. All actual logic lives in
services/ and repositories/ — main.py should stay boring on purpose.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.db.database import init_db
from app.middleware.rate_limit import limiter
from app.routers import ai, auth, chat, health, images, sessions, voice

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("silki.main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting %s (%s)", settings.app_name, settings.environment)
    await init_db()
    yield
    log.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version="3.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# --- Rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS: restricted to configured origins, not "*" ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    log.error("Unhandled error on %s: %s", request.url, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# --- Routers ---
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(images.router)
app.include_router(voice.router)
app.include_router(ai.router)