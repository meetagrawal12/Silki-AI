from fastapi import APIRouter, Depends, File, UploadFile

from app.core.deps import get_current_user
from app.models.user import User
from app.services.voice_service import VoiceService

router = APIRouter(prefix="/voice", tags=["Voice"])

MAX_AUDIO_BYTES = 15 * 1024 * 1024  # 15 MB


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user)
):
    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        from fastapi import HTTPException
        raise HTTPException(413, "Audio file too large (max 15MB)")

    transcript = await VoiceService.transcribe(audio_bytes)
    return {"transcript": transcript}
