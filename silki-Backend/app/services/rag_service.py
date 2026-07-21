"""Local RAG: embed documents, retrieve relevant chunks, no external API needed."""
import logging
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

log = logging.getLogger("silki.rag")

_model = None  # lazy-loaded, avoids slow startup on every reload


def get_embedder():
    global _model
    if _model is None:
        log.info("Loading embedding model (first request only, ~20s)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(__import__("io").BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + chunk_size]))
        i += chunk_size - overlap
    return [c for c in chunks if c.strip()]


def embed_chunks(chunks: list[str]) -> np.ndarray:
    embedder = get_embedder()
    return embedder.encode(chunks, convert_to_numpy=True)


def retrieve_relevant_chunks(
    query: str, chunks: list[str], embeddings: np.ndarray, top_k: int = 3
) -> list[str]:
    embedder = get_embedder()
    query_vec = embedder.encode([query], convert_to_numpy=True)[0]

    # cosine similarity
    norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_vec)
    norms[norms == 0] = 1e-10
    scores = embeddings @ query_vec / norms

    top_indices = np.argsort(scores)[::-1][:top_k]
    return [chunks[i] for i in top_indices]