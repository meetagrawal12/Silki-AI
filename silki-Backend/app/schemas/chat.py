from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator


class ChatRequest(BaseModel):
    session_id: Optional[str] = None  # omit to create a new session
    message: str
    model: Optional[str] = None  # user-selected model override
    temperature: float = 0.7

    @field_validator("message")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > 8000:
            raise ValueError("Message too long (max 8000 chars)")
        return v

    @field_validator("temperature")
    @classmethod
    def clamp_temp(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    model_used: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    model_used: str


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailOut(SessionOut):
    system_prompt: Optional[str] = None
    messages: List[MessageOut]


class SessionUpdateRequest(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None
