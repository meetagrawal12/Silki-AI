"""Detects what the user wants from plain text, so the frontend
never needs mode buttons — one input box handles everything."""
import re

IMAGE_GEN_PATTERNS = [
    r"\b(generate|create|draw|make)\b.*\b(image|picture|photo|art)\b",
    r"\bimagine\b.*\bof\b",
]
SEARCH_PATTERNS = [
    r"\b(search|look up|find out|latest|news about|current)\b",
]


def detect_intent(text: str) -> str:
    lowered = text.lower()
    for pattern in IMAGE_GEN_PATTERNS:
        if re.search(pattern, lowered):
            return "image"
    for pattern in SEARCH_PATTERNS:
        if re.search(pattern, lowered):
            return "search"
    return "chat"