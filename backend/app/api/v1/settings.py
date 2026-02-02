"""Settings API endpoints."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.constants.settings_defaults import DEFAULT_SETTINGS

router = APIRouter(prefix="/settings", tags=["settings"])


class UserSettings(BaseModel):
    """Pydantic model for user settings with validation."""

    llm_provider: Literal["gemini", "anthropic"] = Field(
        default=DEFAULT_SETTINGS["llm_provider"],
        description="LLM provider to use for AI operations",
    )
    language: str = Field(
        default=DEFAULT_SETTINGS["language"],
        min_length=2,
        max_length=5,
        description="Language code (e.g., 'es', 'en')",
    )
    theme: Literal["light", "dark"] = Field(
        default=DEFAULT_SETTINGS["theme"],
        description="UI theme preference",
    )
    articles_per_source: int = Field(
        default=DEFAULT_SETTINGS["articles_per_source"],
        ge=1,
        le=20,
        description="Number of articles to fetch per source",
    )
    max_sources_per_briefing: int = Field(
        default=DEFAULT_SETTINGS["max_sources_per_briefing"],
        ge=1,
        le=20,
        description="Maximum number of sources per briefing",
    )
    min_relevance_score: int = Field(
        default=DEFAULT_SETTINGS["min_relevance_score"],
        ge=0,
        le=10,
        description="Minimum relevance score (0-10) for sources",
    )


class SettingsResponse(BaseModel):
    """Response model for settings update."""

    status: str
    settings: UserSettings


@router.get("", response_model=UserSettings)
async def get_settings() -> UserSettings:
    """
    Get current user settings.

    For now, returns from a mock user. In production, would fetch from DB
    based on authenticated user.
    """
    # TODO: Get actual user from auth context
    # user = await get_current_user(session)
    # return user.settings

    return UserSettings(**DEFAULT_SETTINGS)


@router.post("", response_model=SettingsResponse)
async def update_settings(settings: UserSettings) -> SettingsResponse:
    """
    Update user settings.

    Accepts partial updates - only the provided keys will be updated.
    """
    # TODO: Get actual user from auth context and update in DB
    # user = await get_current_user(session)
    # user.settings = {**user.settings, **settings.model_dump()}
    # session.add(user)
    # await session.commit()

    return SettingsResponse(
        status="success",
        settings=settings,
    )
