"""Search Service for finding news sources."""

import asyncio
from typing import Any
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from app.config import get_settings

class SearchService:
    """Service for searching web content using Google API with scraping fallback."""

    def __init__(self):
        self.settings = get_settings()
        self.http_client = httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
            follow_redirects=True
        )

    async def search(self, query: str, num_results: int = 10) -> list[dict[str, Any]]:
        """
        Search for a query and return list of results with title, link, snippet.
        Prioritizes Tavily -> Google API -> Fallback.
        """
        results = []
        
        # 1. Try Tavily
        if self.settings.tavily_api_key:
            try:
                results = await self._search_tavily(query, num_results)
                if results:
                    return results
            except Exception as e:
                print(f"Tavily search failed: {e}")

        # 2. Try Google API
        if self.settings.google_search_api_key and self.settings.google_search_engine_id:
            try:
                results = await self._search_google_api(query, num_results)
                if results:
                    return results
            except Exception as e:
                print(f"Google API search failed: {e}")
                # Log error and continue to fallback
        
        # 3. Fallback to DuckDuckGo/Bing scraping
        # Note: DDG is often blocked, Bing/Google html can be parsed carefully
        print("Falling back to scraping search...")
        return await self._search_fallback(query, num_results)

    async def _search_tavily(self, query: str, num: int) -> list[dict[str, Any]]:
        """Use Tavily Search API."""
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": num,
            "include_domains": [],
            "exclude_domains": []
        }
        
        resp = await self.http_client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title"),
                "link": item.get("url"),
                "snippet": item.get("content"),
                "source": "tavily"
            })
        return results

    async def _search_google_api(self, query: str, num: int) -> list[dict[str, Any]]:
        """Use Google Custom Search JSON API."""
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.settings.google_search_api_key,
            "cx": self.settings.google_search_engine_id,
            "q": query,
            "num": min(num, 10),  # API limits to 10 per request
        }
        
        resp = await self.http_client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        
        results = []
        for item in data.get("items", []):
            results.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
                "source": "google_api"
            })
        return results

    async def _search_fallback(self, query: str, num: int) -> list[dict[str, Any]]:
        """Fallback using DuckDuckGo HTML scraping (Lite version is easier to scrape)."""
        # Using html.duckduckgo.com which is lighter and easier to parse than the JS version
        url = "https://html.duckduckgo.com/html/"
        data = {"q": query}
        
        try:
            resp = await self.http_client.post(url, data=data)
            
            # If rate limited or blocked, try Bing as second fallback
            if resp.status_code != 200:
                return []
                
            soup = BeautifulSoup(resp.text, "lxml")
            
            results = []
            # DDG lite structure: .result -> .result__a (link) + .result__snippet
            for i, res in enumerate(soup.select(".result")):
                if i >= num:
                    break
                    
                link_tag = res.select_one(".result__a")
                snippet_tag = res.select_one(".result__snippet")
                
                if link_tag:
                    title = link_tag.get_text(strip=True)
                    link = link_tag.get("href")
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    
                    # DDG sometime wraps links
                    if link:
                        results.append({
                            "title": title,
                            "link": link,
                            "snippet": snippet,
                            "source": "ddg_scrape"
                        })
            
            return results
            
        except Exception as e:
            print(f"Fallback search failed: {e}")
            return []

    async def close(self):
        await self.http_client.aclose()
