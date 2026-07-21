import io
import edge_tts

DEFAULT_VOICE = "en-US-AriaNeural"


async def text_to_speech(text: str, voice: str = DEFAULT_VOICE) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])
    return buffer.getvalue()