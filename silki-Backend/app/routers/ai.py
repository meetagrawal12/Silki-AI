"""
Additional AI providers and tools for Silki AI:
multi-model chat, Gemini, web search, vision, RAG, TTS.
"""
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.middleware.rate_limit import limiter
from app.services.gemini_service import GeminiError, gemini_chat, gemini_vision
from app.services.search_service import SearchError, web_search
from app.services.model_router import route_chat
from app.services.rag_service import (
    chunk_text,
    embed_chunks,
    extract_text_from_pdf,
    retrieve_relevant_chunks,
)
from app.services.doc_store import get_document, save_document
from app.services.tts_service import text_to_speech
from app.services.llm_service import groq_chat  # ⚠️ confirm this matches your real function

log = logging.getLogger("silki.ai_router")
router = APIRouter(prefix="/ai", tags=["ai"])


# ---------- Schemas ----------

class GeminiRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    model: str = "gemini-2.5-flash-lite"


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_results: int = Field(default=5, ge=1, le=10)


class ModelChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    provider: str = "groq"  # groq | gemini | openrouter
    model: str = ""


class RAGQuery(BaseModel):
    session_id: str
    question: str = Field(..., min_length=1, max_length=1000)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    voice: str = "en-US-AriaNeural"


# ---------- Multi-model chat ----------

@router.post("/chat")
@limiter.limit("15/minute")
async def multi_model_chat(request: Request, body: ModelChatRequest):
    try:
        result = await route_chat(body.prompt, body.provider, body.model)
        return {"response": result, "provider": body.provider}
    except Exception as e:
        log.error("Multi-model chat error (%s): %s", body.provider, e)
        raise HTTPException(status_code=502, detail=str(e))


# ---------- Gemini ----------

@router.post("/gemini")
@limiter.limit("15/minute")
async def gemini_endpoint(request: Request, body: GeminiRequest):
    try:
        result = await gemini_chat(body.prompt, body.model)
        return {"response": result, "model": body.model}
    except GeminiError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ---------- Web search ----------

@router.post("/search")
@limiter.limit("15/minute")
async def search_endpoint(request: Request, body: SearchRequest):
    try:
        result = await web_search(body.query, body.max_results)
        return result
    except SearchError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ---------- Vision (image understanding) ----------

@router.post("/vision")
@limiter.limit("10/minute")
async def vision_endpoint(
    request: Request,
    prompt: str = Form(...),
    file: UploadFile = File(...),
):
    image_bytes = await file.read()
    try:
        result = await gemini_vision(prompt, image_bytes, file.content_type or "image/jpeg")
        return {"response": result}
    except GeminiError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ---------- RAG: document upload + Q&A ----------

@router.post("/rag/upload")
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    content = await file.read()
    if file.filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf(content)
    else:
        text = content.decode("utf-8", errors="ignore")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No extractable text found in file")

    chunks = chunk_text(text)
    embeddings = embed_chunks(chunks)
    save_document(session_id, chunks, embeddings)

    return {"status": "indexed", "chunks_count": len(chunks)}


@router.post("/rag/ask")
@limiter.limit("15/minute")
async def ask_document(request: Request, body: RAGQuery):
    doc = get_document(body.session_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="No document uploaded for this session")

    relevant = retrieve_relevant_chunks(body.question, doc["chunks"], doc["embeddings"])
    context = "\n\n".join(relevant)

    prompt = f"Answer using only this context:\n\n{context}\n\nQuestion: {body.question}"
    try:
        answer = await groq_chat(prompt)
    except Exception as e:
        log.error("RAG answer generation failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))

    return {"answer": answer, "context_used": relevant}


# ---------- Text-to-speech ----------

@router.post("/tts")
@limiter.limit("10/minute")
async def tts_endpoint(request: Request, body: TTSRequest):
    try:
        audio_bytes = await text_to_speech(body.text, body.voice)
    except Exception as e:
        log.error("TTS failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    return Response(content=audio_bytes, media_type="audio/mpeg")