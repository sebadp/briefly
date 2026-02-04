"""Gemini-powered web scraper agent for extracting article content.

Alternative to Claude scraper, using Google's Gemini model.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup, Tag
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
Extract the article information and return it as a JSON object with these fields:
- title: The article headline (string)
- summary: A 2-3 sentence summary of the article (string, max 300 chars)
- author: The author name (string or null)
- published_at: The publication date in ISO format YYYY-MM-DD (string or null)
- image_url: The main article image URL (string or null)
- full_content: The main article text, first 500 chars only (string)

HTML Content:
{html_content}

IMPORTANT: Return ONLY a valid JSON object. No markdown, no code blocks, no explanations.
Ensure all strings are properly escaped (no unescaped newlines or quotes in values)."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.0-flash"
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        )

    async def fetch_page(self, url: str) -> str:
        """Fetch HTML content from a URL."""
        response = await self.http_client.get(url)
        response.raise_for_status()
        return response.text

    async def detect_rss_feed(self, url: str) -> str | None:
        """Attempt to find an RSS feed URL from the homepage."""
        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, "lxml")

            # 1. Check standard <link> tags
            feed_link = soup.find("link", type="application/rss+xml")
            if feed_link and hasattr(feed_link, "get"):
                href = feed_link.get("href")
                if isinstance(href, str):
                    return href

            feed_link = soup.find("link", type="application/atom+xml")
            if feed_link and hasattr(feed_link, "get"):
                href = feed_link.get("href")
                if isinstance(href, str):
                    return href

            # 2. Check for common patterns if no tag found (heuristic)
            # This is risky without verify, so we stick to tags only for reliability logic

            return None
        except Exception:
            return None

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
            import re

            # Clean markdown code blocks if present
            text = (response.text or "").strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]

            # Additional cleaning for common JSON issues
            # 1. Remove control characters that break JSON
            text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)

            # 2. Try to find the JSON object boundaries
            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                text = json_match.group(0)

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
        except (json.JSONDecodeError, KeyError):
            # Fallback: try regex extraction from the raw response
            import re

            raw = response.text or ""

            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', raw)
            summary_match = re.search(r'"summary"\s*:\s*"([^"]+)"', raw)
            author_match = re.search(r'"author"\s*:\s*"([^"]+)"', raw)

            title = title_match.group(1) if title_match else None
            summary = summary_match.group(1) if summary_match else None

            # If regex extracted data, use it
            if title or summary:
                return ScrapedArticle(
                    title=title or "Untitled",
                    summary=summary or "No summary available",
                    url=url,
                    source_name=source_name or self._extract_domain(url),
                    author=author_match.group(1) if author_match else None,
                )

            # Last resort: basic BeautifulSoup extraction
            soup = BeautifulSoup(html, "lxml")
            title = soup.title.string if soup.title else "Untitled"

            # Try to get first paragraph as summary
            first_p = soup.find("p")
            fallback_summary = (
                first_p.get_text(strip=True)[:300] if first_p else "Could not extract content"
            )

            return ScrapedArticle(
                title=title or "Untitled",
                summary=fallback_summary,
                url=url,
                source_name=source_name or self._extract_domain(url),
            )

    async def scrape_articles(self, urls: list[str], source_name: str = "") -> list[ScrapedArticle]:
        """Scrape multiple articles."""
        articles = []
        # TODO: Run in parallel
        for url in urls:
            try:
                article = await self.scrape_article(url, source_name)
                articles.append(article)
            except Exception as e:
                print(f"Error scraping {url}: {e}")
        return articles

    async def scrape_multiple_from_homepage(self, url: str, limit: int = 5) -> list[ScrapedArticle]:
        """
        Scrape multiple full articles from a homepage using Gemini.
        Note: Gemini agent doesn't have a specific list extractor yet,
        so we'll extract links from HTML using BS4 first.
        """
        html = await self.fetch_page(url)
        soup = BeautifulSoup(html, "lxml")

        # Simple heuristic to find article links
        # Look for links inside typical article containers
        article_urls = set()
        domain = self._extract_domain(url)

        from urllib.parse import urljoin, urlparse

        base_domain = urlparse(url).netloc

        for a in soup.find_all("a", href=True):
            if not isinstance(a, Tag):
                continue
            href = a.get("href")
            if not isinstance(href, str):
                continue
            full_url = urljoin(url, href)
            if urlparse(full_url).netloc == base_domain:
                # Avoid root, admin, tag, etc.
                path = urlparse(full_url).path

                # Heuristic: Avoid common non-article paths
                path_lower = str(path).lower()

                # Exclude obvious non-articles
                if any(
                    x in path_lower
                    for x in [
                        "/tag/",
                        "/category/",
                        "/author/",
                        "/login",
                        "/signup",
                        "/contact",
                        "/policy",
                        "/terms",
                        "/cookies",
                        "/pricing",
                        "/features",
                        "/product",
                        "/careers",
                        "/about",
                        "/legal",
                        "/security",
                    ]
                ):
                    continue

                # Strict Mode: URL must look like an article
                # (contains date or /news/, /blog/, /post/, or is significantly long with dashes)
                is_likely_article = False

                if path and len(path) > 20 and "-" in path:
                    is_likely_article = True
                elif any(
                    x in path_lower
                    for x in ["/news/", "/blog/", "/press/", "/posts/", "/2024/", "/2025/"]
                ):
                    is_likely_article = True

                if is_likely_article:
                    article_urls.add(full_url)

        # Limit to requested count (request extra to account for failures)
        # +3 buffer
        to_scrape = list(article_urls)[: limit + 3]

        # Fallback: finding zero links usually means SPA or JS rendering
        if not to_scrape and len(html) > 0:
            import re
            # Regex to find http/https links in the same domain
            pattern = fr'https?://{re.escape(base_domain)}/[^\s"\'<>]+'
            matches = re.findall(pattern, html)
            
            for m in matches:
                # Clean up occasional trailing characters from JS strings
                m = m.split('\\')[0].split('"')[0].split("'")[0]
                
                path = urlparse(m).path
                path_lower = str(path).lower()
                
                # Apply same filtering logic
                if any(x in path_lower for x in ["/tag/", "/category/", "/author/", "/login", "/signup", 
                                               "/contact", "/policy", "/terms", "/cookies", "/pricing"]):
                    continue
                    
                # Relaxed SPA check - accept if it has some path segments
                if len(path) > 3 and path != "/":
                     article_urls.add(m)
            
            to_scrape = list(article_urls)[: limit + 3]

        articles = await self.scrape_articles(to_scrape, source_name=domain)

        # Post-validation: Ensure content is not a policy page
        valid_articles = [a for a in articles if self._is_meaningful_article(a)]

        # Return only the requested amount
        return valid_articles[:limit]

    def _is_meaningful_article(self, article: ScrapedArticle) -> bool:
        """Check if article looks like real content, not a policy/cookie page."""
        if not article.title or not article.summary:
            return False

        title_lower = article.title.lower()
        if any(
            x in title_lower
            for x in [
                "cookie",
                "privacy policy",
                "aviso legal",
                "terminos",
                "conditions",
                "subscribe",
                "login",
                "politica",
            ]
        ):
            return False

        # Stricter length check
        if len(article.summary) < 50:
            return False

        # Check against "Untitled" and "Home"
        if article.title.strip().lower() in ["untitled", "home", "homepage", "index", "welcome"]:
            return False

        return True

    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain.split(".")[0].title()

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()


# Factory function to get the appropriate scraper
def get_scraper_agent() -> Any:
    """Get scraper agent based on configured LLM provider."""
    settings = get_settings()

    if settings.llm_provider == "gemini":
        return GeminiScraperAgent()
    else:
        # Default to Claude
        from app.agents.scraper_agent import ScraperAgent

        return ScraperAgent()
