from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, field_validator

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.services.image_service import ImageService
from app.services.llm_service import LLMService

router = APIRouter(prefix="/images", tags=["Images"])
settings = get_settings()


class ImageRequest(BaseModel):
    prompt: str

    @field_validator("prompt")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Prompt cannot be empty")
        if len(v) > 2000:
            raise ValueError("Prompt too long (max 2000 chars)")
        return v


class ImageResponse(BaseModel):
    image_base64: str
    prompt: str


class EnhanceRequest(BaseModel):
    prompt: str


class EnhanceResponse(BaseModel):
    enhanced: str
    original: str


@router.post("/generate", response_model=ImageResponse)
@limiter.limit(settings.rate_limit_image)
async def generate_image(
    request: Request, data: ImageRequest, current_user: User = Depends(get_current_user)
):
    image_b64 = await ImageService.generate(data.prompt)
    return ImageResponse(image_base64=image_b64, prompt=data.prompt)


@router.post("/enhance-prompt", response_model=EnhanceResponse)
async def enhance_prompt(data: EnhanceRequest, current_user: User = Depends(get_current_user)):
    instruction = (
        "You are an expert image prompt engineer for FLUX.1 image generation models.\n"
        "Enhance the following user prompt into a detailed, vivid, high-quality image "
        "generation prompt. Add details about lighting, atmosphere, style, composition, "
        "colors, and technical quality keywords. Keep it under 250 words. "
        "Return ONLY the enhanced prompt, no explanation.\n\n"
        f"User prompt: {data.prompt}"
    )
    result = await LLMService().complete(
        [{"role": "user", "content": instruction}], temperature=0.8, max_tokens=300
    )
    return EnhanceResponse(enhanced=result.content.strip().strip('"'), original=data.prompt)
