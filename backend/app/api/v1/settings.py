"""Settings API endpoints."""

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/settings", tags=["settings"])


# Default settings for users without saved preferences
DEFAULT_SETTINGS: dict[str, Any] = {
    "llm_provider": "gemini",
    "language": "es",
    "theme": "dark",
    "articles_per_source": 5,
    "max_sources_per_briefing": 8,
    "min_relevance_score": 7,
}


@router.get("")
async def get_settings() -> dict[str, Any]:
    """
    Get current user settings.

    For now, returns from a mock user. In production, would fetch from DB
    based on authenticated user.
    """
    # TODO: Get actual user from auth context
    # user = await get_current_user(session)
    # return user.settings

    return DEFAULT_SETTINGS


@router.post("")
async def update_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """
    Update user settings.

    Accepts partial updates - only the provided keys will be updated.
    """
    # TODO: Get actual user from auth context and update in DB
    # user = await get_current_user(session)
    # user.settings = {**user.settings, **settings}
    # session.add(user)
    # await session.commit()

    # For now, just merge with defaults and return
    merged = {**DEFAULT_SETTINGS, **settings}

    return {
        "status": "success",
        "settings": merged,
    }
