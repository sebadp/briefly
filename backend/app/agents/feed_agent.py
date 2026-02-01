"""Feed Creation Agent - Interprets natural language queries to create feeds."""

from dataclasses import dataclass
from typing import Any, cast

from strands import Agent
from strands.tools import tool

# Known sources database (in production, this would be in PostgreSQL)
KNOWN_SOURCES = [
    {
        "url": "https://techcrunch.com",
        "name": "TechCrunch",
        "topics": ["tech", "startups", "ai", "technology"],
        "lang": "en",
    },
    {
        "url": "https://theverge.com",
        "name": "The Verge",
        "topics": ["tech", "gadgets", "technology"],
        "lang": "en",
    },
    {
        "url": "https://wired.com",
        "name": "Wired",
        "topics": ["tech", "science", "ai", "technology"],
        "lang": "en",
    },
    {
        "url": "https://arstechnica.com",
        "name": "Ars Technica",
        "topics": ["tech", "science", "technology"],
        "lang": "en",
    },
    {
        "url": "https://hipertextual.com",
        "name": "Hipertextual",
        "topics": ["tech", "ciencia", "tecnología"],
        "lang": "es",
    },
    {
        "url": "https://xataka.com",
        "name": "Xataka",
        "topics": ["tech", "gadgets", "tecnología"],
        "lang": "es",
    },
    {
        "url": "https://infobae.com",
        "name": "Infobae",
        "topics": ["noticias", "argentina", "latam"],
        "lang": "es",
    },
    {
        "url": "https://lanacion.com.ar",
        "name": "La Nación",
        "topics": ["noticias", "argentina", "política"],
        "lang": "es",
    },
    {
        "url": "https://clarin.com",
        "name": "Clarín",
        "topics": ["noticias", "argentina", "deportes"],
        "lang": "es",
    },
    {
        "url": "https://bbc.com/mundo",
        "name": "BBC Mundo",
        "topics": ["noticias", "internacional", "mundo"],
        "lang": "es",
    },
]


@tool  # type: ignore[untyped-decorator]
def search_news_sources(
    topics: list[str],
    language: str = "es",
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """
    Search for relevant news sources based on topics and language.

    Args:
        topics: List of topics to search for (e.g., ["tech", "ai", "startups"])
        language: Preferred language code (es, en)
        max_results: Maximum number of sources to return

    Returns:
        List of matching sources with url, name, and relevance score
    """
    results = []
    topics_lower = [t.lower() for t in topics]

    for source in KNOWN_SOURCES:
        # Calculate relevance score
        score = 0

        # Language match bonus
        if source["lang"] == language:
            score += 2

        # Topic matches
        for topic in topics_lower:
            for source_topic in source["topics"]:
                if topic in source_topic or source_topic in topic:
                    score += 1

        if score > 0:
            results.append(
                {
                    "url": source["url"],
                    "name": source["name"],
                    "language": source["lang"],
                    "relevance_score": score,
                }
            )

    # Sort by relevance and limit
    # Use a typed key function for sorting
    sorted_results = sorted(results, key=lambda x: int(cast(int, x.get("relevance_score", 0))), reverse=True)
    return sorted_results[:max_results]


@tool  # type: ignore[untyped-decorator]
def validate_url(url: str) -> dict[str, Any]:
    """
    Validate if a URL is accessible and appears to be a news source.

    Args:
        url: The URL to validate

    Returns:
        Dict with is_valid, site_name, and detected_type
    """
    from urllib.parse import urlparse

    try:
        # Extract domain for name
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")

        # In production: Actually make the request
        # For now, return optimistic result
        return {
            "is_valid": True,
            "site_name": domain.split(".")[0].title(),
            "url": url,
            "detected_type": "website",
        }
    except Exception as e:
        return {
            "is_valid": False,
            "error": str(e),
            "url": url,
        }


@tool  # type: ignore[untyped-decorator]
def extract_intent(query: str) -> dict[str, Any]:
    """
    Extract structured intent from a natural language query.
    This is a helper tool - the agent should use this to understand the query.

    Args:
        query: The user's natural language description

    Returns:
        Dict with extracted topics, language, region, and any URLs mentioned
    """
    query_lower = query.lower()

    # Detect language preference
    language = "es"  # Default Spanish
    if any(word in query_lower for word in ["english", "in english", "inglés"]):
        language = "en"
    elif any(word in query_lower for word in ["español", "spanish", "en español"]):
        language = "es"

    # Detect region
    region = None
    if "argentina" in query_lower:
        region = "argentina"
    elif "latam" in query_lower or "latinoamérica" in query_lower:
        region = "latam"
    elif "global" in query_lower or "mundial" in query_lower:
        region = "global"

    # Extract potential topics (simple keyword extraction)
    topic_keywords = [
        "tech",
        "tecnología",
        "technology",
        "ai",
        "inteligencia artificial",
        "startups",
        "emprendimiento",
        "ciencia",
        "science",
        "política",
        "deportes",
        "sports",
        "economía",
        "economy",
        "finanzas",
        "finance",
        "climate",
        "clima",
        "environment",
        "medio ambiente",
        "gaming",
        "videojuegos",
        "crypto",
        "blockchain",
        "machine learning",
        "ml",
    ]

    found_topics = []
    for keyword in topic_keywords:
        if keyword in query_lower:
            found_topics.append(keyword)

    # Extract URLs from query
    import re

    url_pattern = r"https?://[^\s]+"
    found_urls = re.findall(url_pattern, query)

    return {
        "original_query": query,
        "detected_language": language,
        "detected_region": region,
        "extracted_topics": found_topics if found_topics else ["general"],
        "mentioned_urls": found_urls,
    }


@dataclass
class FeedConfig:
    """Configuration for a new feed."""

    name: str
    topics: list[str]
    language: str
    sources: list[dict[str, Any]]
    refresh_interval_minutes: int = 60


class FeedCreationAgent:
    """
    Agent that interprets natural language queries to create feed configurations.

    Uses Strands framework with Claude to understand user intent and suggest
    relevant news sources.
    """

    SYSTEM_PROMPT = """Eres un asistente que ayuda a crear feeds de noticias personalizados.

Tu trabajo es:
1. Analizar la petición del usuario en lenguaje natural
2. Usar la herramienta extract_intent para entender qué quiere
3. Buscar fuentes relevantes con search_news_sources
4. Si el usuario menciona URLs específicas, validarlas con validate_url
5. Crear una configuración de feed estructurada

REGLAS:
- Siempre busca al menos 3 fuentes relevantes
- Respeta el idioma preferido del usuario
- Si no hay suficientes fuentes, sugiere alternativas
- Genera un nombre descriptivo para el feed

Responde SIEMPRE con un JSON válido con este formato:
{
    "feed_name": "nombre descriptivo",
    "topics": ["topic1", "topic2"],
    "language": "es",
    "sources": [{"url": "...", "name": "...", "type": "website"}],
    "refresh_interval_minutes": 60
}
"""

    def __init__(self) -> None:
        self.agent = Agent(
            model="claude-sonnet-4-20250514",
            system_prompt=self.SYSTEM_PROMPT,
            tools=[search_news_sources, validate_url, extract_intent],
        )

    async def create_feed_config(self, user_query: str) -> dict[str, Any]:
        """
        Process a natural language query and return feed configuration.

        Args:
            user_query: The user's description of what they want

        Returns:
            Dict with feed configuration
        """
        prompt = f"""El usuario quiere crear un feed de noticias con esta descripción:

"{user_query}"

Analiza la petición, busca fuentes relevantes y genera la configuración del feed."""

        response = await self.agent.run_async(prompt)

        # Parse JSON from response
        import json

        try:
            # Try to extract JSON from response
            text = str(response)
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return cast(dict[str, Any], json.loads(text[start:end]))
        except json.JSONDecodeError:
            pass

        # Fallback: return basic config
        return {
            "feed_name": f"Feed: {user_query[:30]}",
            "topics": ["general"],
            "language": "es",
            "sources": [],
            "refresh_interval_minutes": 60,
            "error": "Could not parse AI response",
        }


# Convenience function for direct use
async def interpret_feed_query(query: str) -> dict[str, Any]:
    """Interpret a natural language query and return feed configuration."""
    agent = FeedCreationAgent()
    return await agent.create_feed_config(query)
