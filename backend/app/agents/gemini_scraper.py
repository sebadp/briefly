"""Gemini-powered web scraper agent for extracting article content.

Alternative to Claude scraper, using Google's Gemini model.
"""

from dataclasses import dataclass
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

from google import genai
from google.genai import types

from app.config import get_settings


@dataclass
class ScrapedArticle:
    """Represents a scraped article."""
    
    title: str
    summary: str
    url: str
    source_name: str
    published_at: datetime | None = None
    author: str | None = None
    image_url: str | None = None
    full_content: str | None = None


class GeminiScraperAgent:
    """Agent that uses Gemini to extract structured data from web pages."""

    EXTRACTION_PROMPT = """Analyze the following HTML content from a news article page.
Extract the article information and return it in JSON format with these fields:
- title: The article headline
- summary: A 2-3 sentence summary of the article
- author: The author name (or null if not found)
- published_at: The publication date in ISO format (or null if not found)
- image_url: The main article image URL (or null if not found)
- full_content: The main article text content

HTML Content:
{html_content}

Return ONLY valid JSON, no markdown formatting."""

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.0-flash"
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        )

    async def fetch_page(self, url: str) -> str:
        """Fetch HTML content from a URL."""
        response = await self.http_client.get(url)
        response.raise_for_status()
        return response.text

    def _clean_html(self, html: str, max_length: int = 50000) -> str:
        """Clean and truncate HTML for processing."""
        soup = BeautifulSoup(html, "lxml")
        
        # Remove scripts, styles, and other noise
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        
        # Get text-relevant HTML
        article = soup.find("article") or soup.find("main") or soup.body
        if article:
            clean_html = str(article)
        else:
            clean_html = str(soup.body) if soup.body else html
        
        # Truncate if too long
        if len(clean_html) > max_length:
            clean_html = clean_html[:max_length] + "..."
        
        return clean_html

    async def scrape_article(self, url: str, source_name: str = "") -> ScrapedArticle:
        """Scrape a single article using Gemini for extraction."""
        # Fetch the page
        html = await self.fetch_page(url)
        clean_html = self._clean_html(html)
        
        # Use Gemini to extract article data
        prompt = self.EXTRACTION_PROMPT.format(html_content=clean_html)
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2000,
            ),
        )
        
        # Parse JSON response
        try:
            import json
            # Clean markdown code blocks if present
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]
            
            data = json.loads(text)
            
            # Parse published_at if present
            published_at = None
            if data.get("published_at"):
                try:
                    published_at = datetime.fromisoformat(
                        data["published_at"].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass
            
            return ScrapedArticle(
                title=data.get("title", "Untitled"),
                summary=data.get("summary", ""),
                url=url,
                source_name=source_name or self._extract_domain(url),
                published_at=published_at,
                author=data.get("author"),
                image_url=data.get("image_url"),
                full_content=data.get("full_content"),
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback to basic extraction
            soup = BeautifulSoup(html, "lxml")
            title = soup.title.string if soup.title else "Untitled"
            
            return ScrapedArticle(
                title=title,
                summary=f"Error extracting article: {e}",
                url=url,
                source_name=source_name or self._extract_domain(url),
            )

    async def scrape_articles(
        self, urls: list[str], source_name: str = ""
    ) -> list[ScrapedArticle]:
        """Scrape multiple articles."""
        articles = []
        for url in urls:
            try:
                article = await self.scrape_article(url, source_name)
                articles.append(article)
            except Exception as e:
                print(f"Error scraping {url}: {e}")
        return articles

    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain.split(".")[0].title()

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


# Factory function to get the appropriate scraper
def get_scraper_agent():
    """Get scraper agent based on configured LLM provider."""
    settings = get_settings()
    
    if settings.llm_provider == "gemini":
        return GeminiScraperAgent()
    else:
        # Default to Claude
        from app.agents.scraper_agent import ScraperAgent
        return ScraperAgent()
