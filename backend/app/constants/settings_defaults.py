"""Default settings constants shared across the application."""

from typing import Any

# Default settings for new users
DEFAULT_SETTINGS: dict[str, Any] = {
    "llm_provider": "gemini",
    "language": "es",
    "theme": "dark",
    "articles_per_source": 5,
    "max_sources_per_briefing": 8,
    "min_relevance_score": 7,
}
