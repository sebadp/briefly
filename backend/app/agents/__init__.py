"""Agents package - AI/LLM agents using Strands, Claude, and Gemini."""

from app.agents.feed_agent import FeedCreationAgent, interpret_feed_query
from app.agents.gemini_scraper import (
    GeminiScraperAgent,
    ScrapedArticle,
    get_scraper_agent,
)
from app.agents.scraper_agent import (
    ExtractedArticle,
    ScraperAgent,
    scrape_single_article,
    scrape_source_homepage,
)

__all__ = [
    # Feed agent
    "FeedCreationAgent",
    "interpret_feed_query",
    # Claude scraper
    "ScraperAgent",
    "ExtractedArticle",
    "scrape_single_article",
    "scrape_source_homepage",
    # Gemini scraper
    "GeminiScraperAgent",
    "ScrapedArticle",
    "get_scraper_agent",
]
