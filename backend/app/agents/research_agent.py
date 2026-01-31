"""Research Agent for finding and validating news sources with streaming capabilities."""

import asyncio
import json
from datetime import datetime, UTC
from typing import AsyncGenerator, Any

from app.services.search_service import SearchService
from app.agents import get_scraper_agent
from app.config import get_settings

class ResearchAgent:
    """
    Agent that performs deep research to find news sources for a topic.
    Designed for streaming output of its thought process.
    """

    def __init__(self):
        self.search_service = SearchService()
        self.settings = get_settings()

    async def research_topic(self, topic: str) -> AsyncGenerator[str, None]:
        """
        Research a topic and yield streaming events.
        Events are JSON strings in SSE format.
        """
        try:
            # 1. Plan
            yield self._event("log", f"🤖 Iniciando investigación para: '{topic}'")
            yield self._event("log", "🧠 Generando queries de búsqueda...")
            
            queries = [
                f'best news websites for {topic}',
                f'top {topic} news sources blogs',
                f'{topic} news aggregate',
            ]
            
            # Additional localized queries if needed (heuristic)
            if any(w in topic.lower() for w in ["argentina", "chile", "latam", "español"]):
                queries.append(f'mejores sitios noticias {topic}')
            
            yield self._event("log", f"🔍 Queries generadas: {', '.join(queries)}")

            # 2. Search
            seen_domains = set()  # Track domains we've already added
            candidates = []  # List of candidate dicts
            
            for q in queries:
                yield self._event("log", f"🌐 Buscando en Google: '{q}'...")
                results = await self.search_service.search(q, num_results=5)
                
                for res in results:
                    link = res.get("link")
                    if link:
                        # Extract domain to avoid duplicates and subpages
                        domain = self._extract_base_url(link)
                        if domain and domain not in seen_domains:
                            seen_domains.add(domain)
                            candidates.append({
                                "base": domain, 
                                "full": link, 
                                "title": res.get("title")
                            })
                            
                yield self._event("log", f"✅ Encontrados {len(results)} resultados para '{q}'")
                await asyncio.sleep(0.5) # Artificial delay for UX pacing

            yield self._event("log", f"📊 Total candidatos únicos: {len(candidates)}. Filtrando...")

            # 3. Validate & Filter
            valid_sources = []
            scraper = get_scraper_agent()
            
            for i, cand in enumerate(candidates[:8]): # check top 8 to save time
                url = cand["base"]
                yield self._event("log", f"🕵️ Validando accesibilidad: {url}")
                
                try:
                    # Quick validation scrape
                    # We just want to see if it has recent articles
                    articles = await scraper.scrape_multiple_from_homepage(url, limit=3)
                    
                    if articles and len(articles) > 0:
                        yield self._event("log", f"✨ Válido: {url} ({len(articles)} artículos recientes)")
                        valid_sources.append({
                            "url": url,
                            "name": cand["title"] or self._extract_name(url),
                            "article_count": len(articles),
                            "last_article": articles[0].title
                        })
                    else:
                        yield self._event("log", f"⚠️ Descartado: {url} (No se encontraron artículos automáticamente)")
                
                except Exception as e:
                    yield self._event("log", f"❌ Error accediendo a {url}: {str(e)[:50]}")
                
            await scraper.close()

            # 4. Final Result
            if valid_sources:
                yield self._event("log", f"🎉 Investigación completada. {len(valid_sources)} fuentes encontradas.")
                yield self._event("result", {
                    "topic": topic,
                    "sources": valid_sources,
                    "created_at": datetime.now(UTC).isoformat()
                })
            else:
                yield self._event("log", "😓 No se encontraron fuentes válidas que pudieran ser scrapeadas automáticamente.")
                yield self._event("error", "No sources found")

        except Exception as e:
            yield self._event("error", str(e))
        finally:
            await self.search_service.close()

    def _event(self, type: str, data: Any) -> str:
        """Format as SSE event."""
        return json.dumps({"type": type, "data": data}) + "\n"

    def _extract_base_url(self, url: str) -> str:
        """Get the base URL (homepage) from a deep link."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _extract_name(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "").split(".")[0].title()

    async def close(self):
        await self.search_service.close()
