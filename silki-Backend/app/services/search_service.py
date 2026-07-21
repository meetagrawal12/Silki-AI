"""Tavily web search service — Perplexity-style search + citations."""
import logging

import httpx

from app.core.config import get_settings

log = logging.getLogger("silki.search")
settings = get_settings()

TAVILY_URL = "https://api.tavily.com/search"


class SearchError(RuntimeError):
    pass


async def web_search(query: str, max_results: int = 5) -> dict:
    if not settings.tavily_api_key:
        raise SearchError("TAVILY_API_KEY is not configured")

    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": True,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(TAVILY_URL, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            log.error("Tavily API error: %s — %s", e.response.status_code, e.response.text)
            raise SearchError(f"Tavily API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            log.error("Tavily request failed: %s", e)
            raise SearchError("Could not reach Tavily API") from e

        data = resp.json()

    return {
        "answer": data.get("answer"),
        "sources": [
            {"title": r.get("title"), "url": r.get("url"), "content": r.get("content")}
            for r in data.get("results", [])
        ],
    }