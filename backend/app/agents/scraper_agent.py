"""Web Scraper Agent - Uses Claude to extract structured content from news pages."""

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any
import json
import re

import anthropic
import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings


@dataclass
class ExtractedArticle:
    """Structured article data extracted from a web page."""
    title: str
    summary: str
    url: str
    source_url: str
    source_name: str
    published_at: datetime | None = None
    author: str | None = None
    thumbnail_url: str | None = None


@dataclass
class ScraperConfig:
    """Configuration for the scraper."""
    max_html_chars: int = 50000
    model: str = "claude-sonnet-4-20250514"
    timeout_seconds: int = 30
    max_summary_words: int = 200


class ScraperAgent:
    """
    AI-powered web scraper that uses Claude to extract structured article data.
    
    Unlike traditional scrapers with CSS selectors, this scraper sends cleaned HTML
    to Claude and asks it to extract the relevant information, making it resilient
    to layout changes and working across different sites without configuration.
    """
    
    EXTRACTION_PROMPT = """Analiza este HTML de una página de noticias y extrae la información del artículo.

URL de la página: {url}

Extrae los siguientes campos:
1. title: El título principal del artículo (no el del sitio)
2. summary: Un resumen del contenido en 2-3 oraciones (máximo {max_words} palabras)
3. published_date: Fecha de publicación en formato ISO (YYYY-MM-DD) o null si no está clara
4. author: Nombre del autor o null si no está disponible
5. main_image_url: URL de la imagen principal del artículo o null

HTML (limpio):
```html
{html}
```

Responde ÚNICAMENTE con JSON válido, sin explicaciones ni markdown:
{{"title": "...", "summary": "...", "published_date": "...", "author": "...", "main_image_url": "..."}}
"""

    LIST_EXTRACTION_PROMPT = """Analiza este HTML de una página de listado de noticias (portada o índice).

URL de la página: {url}

Extrae TODOS los artículos/noticias visibles en la página. Para cada uno extrae:
- title: Título del artículo
- url: URL del artículo (puede ser relativa)
- snippet: Texto preview/descripción si existe

Responde ÚNICAMENTE con JSON válido:
{{"articles": [{{"title": "...", "url": "...", "snippet": "..."}}, ...]}}
"""

    def __init__(self, config: ScraperConfig | None = None):
        self.config = config or ScraperConfig()
        self.settings = get_settings()
        self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        self.http = httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        )

    async def _fetch_html(self, url: str) -> str:
        """Fetch and clean HTML from a URL."""
        response = await self.http.get(url)
        response.raise_for_status()
        return response.text

    def _clean_html(self, html: str) -> str:
        """Remove unnecessary elements and limit size."""
        soup = BeautifulSoup(html, "lxml")
        
        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", 
                         "iframe", "noscript", "svg", "form", "aside"]):
            tag.decompose()
        
        # Remove comments
        for comment in soup.find_all(string=lambda t: isinstance(t, str) and t.strip().startswith("<!--")):
            comment.extract()
        
        # Try to find main content area
        main = soup.find("main") or soup.find("article") or soup.find(class_=re.compile(r"content|article|post"))
        if main:
            content = str(main)
        else:
            content = str(soup.body) if soup.body else str(soup)
        
        # Limit size
        return content[:self.config.max_html_chars]

    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL for source identification."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain.split(".")[0].title()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_claude(self, prompt: str) -> str:
        """Call Claude API with retry logic."""
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def scrape_article(self, url: str) -> ExtractedArticle | None:
        """
        Scrape a single article page and extract structured data.
        
        Args:
            url: URL of the article to scrape
            
        Returns:
            ExtractedArticle with title, summary, etc. or None if failed
        """
        try:
            # Fetch and clean HTML
            html = await self._fetch_html(url)
            clean_html = self._clean_html(html)
            
            # Build prompt
            prompt = self.EXTRACTION_PROMPT.format(
                url=url,
                html=clean_html,
                max_words=self.config.max_summary_words,
            )
            
            # Call Claude
            response_text = await self._call_claude(prompt)
            
            # Parse JSON response
            data = json.loads(response_text)
            
            # Parse date if present
            published_at = None
            if data.get("published_date"):
                try:
                    published_at = datetime.fromisoformat(data["published_date"])
                except ValueError:
                    pass
            
            return ExtractedArticle(
                title=data.get("title", "Untitled"),
                summary=data.get("summary", ""),
                url=url,
                source_url=url,
                source_name=self._extract_domain(url),
                published_at=published_at,
                author=data.get("author"),
                thumbnail_url=data.get("main_image_url"),
            )
            
        except httpx.HTTPError as e:
            print(f"HTTP error scraping {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse Claude response for {url}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error scraping {url}: {e}")
            return None

    async def scrape_article_list(self, url: str) -> list[dict[str, Any]]:
        """
        Scrape a page listing multiple articles (e.g., homepage, category page).
        
        Args:
            url: URL of the list page
            
        Returns:
            List of dicts with title, url, snippet for each article found
        """
        try:
            html = await self._fetch_html(url)
            clean_html = self._clean_html(html)
            
            prompt = self.LIST_EXTRACTION_PROMPT.format(url=url, html=clean_html)
            response_text = await self._call_claude(prompt)
            
            data = json.loads(response_text)
            articles = data.get("articles", [])
            
            # Normalize URLs (convert relative to absolute)
            from urllib.parse import urljoin
            for article in articles:
                if article.get("url") and not article["url"].startswith("http"):
                    article["url"] = urljoin(url, article["url"])
            
            return articles
            
        except Exception as e:
            print(f"Error scraping article list from {url}: {e}")
            return []

    async def scrape_multiple_from_homepage(
        self, url: str, limit: int = 5
    ) -> list[ExtractedArticle]:
        """
        Scrape multiple full articles from a homepage/list URL.

        Args:
            url: URL of the homepage or section
            limit: Maximum number of articles to scrape

        Returns:
            List of fully scraped ExtractedArticle objects
        """
        # 1. Get list of article headers/links
        article_links = await self.scrape_article_list(url)
        
        if not article_links:
            return []
            
        # 2. Limit to requested count
        to_scrape = article_links[:limit]
        
        # 3. Scrape in parallel
        results = []
        import asyncio
        
        tasks = []
        for item in to_scrape:
            if item.get("url"):
                tasks.append(self.scrape_article(item["url"]))
                
        # Wait for all
        scraped = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 4. Filter successful results
        for res in scraped:
            if isinstance(res, ExtractedArticle):
                results.append(res)
                
        return results

    async def close(self):
        """Close the HTTP client."""
        await self.http.aclose()


# Convenience functions
async def scrape_single_article(url: str) -> ExtractedArticle | None:
    """Scrape a single article URL."""
    scraper = ScraperAgent()
    try:
        return await scraper.scrape_article(url)
    finally:
        await scraper.close()


async def scrape_source_homepage(url: str) -> list[dict[str, Any]]:
    """Scrape article links from a source's homepage."""
    scraper = ScraperAgent()
    try:
        return await scraper.scrape_article_list(url)
    finally:
        await scraper.close()
