"""Research endpoints."""

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.agents.research_agent import ResearchAgent

router = APIRouter()


@router.get("/stream")
async def stream_research(
    topic: str,
    articles_per_source: int = Query(default=5, ge=1, le=10),
    max_sources: int = Query(default=8, ge=3, le=15),
    min_relevance: int = Query(default=7, ge=1, le=10),
    language: str = Query(default="es"),
) -> StreamingResponse:
    """
    Stream research progress for a given topic.
    Returns Server-Sent Events (SSE).

    Settings:
    - articles_per_source: How many articles to scrape per source (1-10)
    - max_sources: Maximum sources to find (3-15)
    - min_relevance: Minimum relevance score filter (1-10)
    - language: Response language (es/en)
    """
    agent = ResearchAgent()

    user_settings: dict[str, Any] = {
        "articles_per_source": articles_per_source,
        "max_sources_per_briefing": max_sources,
        "min_relevance_score": min_relevance,
        "language": language,
    }

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event_data in agent.research_topic(topic, user_settings):
                # SSE format: data: <content>\n\n
                yield f"data: {event_data}\n\n"
        finally:
            await agent.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
