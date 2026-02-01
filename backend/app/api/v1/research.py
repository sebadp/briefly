"""Research endpoints."""

from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents.research_agent import ResearchAgent

router = APIRouter()


@router.get("/stream")
async def stream_research(topic: str) -> StreamingResponse:
    """
    Stream research progress for a given topic.
    Returns Server-Sent Events (SSE).
    """
    agent = ResearchAgent()

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event_data in agent.research_topic(topic):
                # SSE format: data: <content>\n\n
                yield f"data: {event_data}\n\n"
        finally:
            await agent.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
