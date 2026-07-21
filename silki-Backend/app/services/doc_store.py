"""Very simple in-memory document store, keyed by session_id.
Fine for dev/small scale — swap for Chroma/FAISS later if you need persistence."""
_STORE: dict[str, dict] = {}


def save_document(session_id: str, chunks: list[str], embeddings) -> None:
    _STORE[session_id] = {"chunks": chunks, "embeddings": embeddings}


def get_document(session_id: str) -> dict | None:
    return _STORE.get(session_id)