"""Research Agent for finding and validating news sources with streaming capabilities."""

import asyncio
import json
from datetime import datetime, UTC
from typing import AsyncGenerator, Any

from app.services.search_service import SearchService
from app.agents import get_scraper_agent
from app.config import get_settings

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # Handle missing dependency gracefully

class ResearchAgent:
    """
    Agent that performs deep research to find news sources for a topic.
    Designed for streaming output of its thought process.
    """

    def __init__(self):
        self.search_service = SearchService()
        self.settings = get_settings()
        
        # Initialize Gemini if available
        self.client = None
        if self.settings.gemini_api_key and genai:
            self.client = genai.Client(api_key=self.settings.gemini_api_key)
            self.model = "gemini-2.0-flash"

    async def research_topic(self, topic: str) -> AsyncGenerator[str, None]:
        """
        Research a topic and yield streaming events.
        Events are JSON strings in SSE format.
        """
        try:
            # 1. Plan (LLM vs Heuristic)
            yield self._event("log", f"🤖 Iniciando investigación para: '{topic}'")
            
            if self.client:
                yield self._event("log", "🧠 Generando queries inteligentes con AI...")
                queries = await self._generate_queries_with_llm(topic)
            else:
                yield self._event("log", "🧠 Generando queries (Modo básico)...")
                queries = [
                    f'best news websites for {topic}',
                    f'top {topic} news sources blogs',
                    f'{topic} news aggregate',
                ]
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
                    articles = await scraper.scrape_multiple_from_homepage(url, limit=4)
                    
                    if not articles or len(articles) == 0:
                        yield self._event("log", f"⚠️ Descartado: {url} (Sin artículos accesibles)")
                        continue

                    # Validation 1: Frequency Check (Active in last 3 months?)
                    valid_freq, last_date = self._check_frequency(articles)
                    if not valid_freq:
                        yield self._event("log", f"🕰️ Descartado: {url} (Inactivo, último artículo: {last_date})")
                        continue

                    # Validation 2: Relevance Score (LLM)
                    relevance_score, reason = 10, "Heuristic pass"
                    if self.client:
                        relevance_score, reason = await self._score_relevance(topic, articles)
                    
                    if relevance_score >= 7:
                        yield self._event("log", f"✨ Válido: {url} (Score: {relevance_score}/10 - {len(articles)} arts)")
                        valid_sources.append({
                            "url": url,
                            "name": cand["title"] or self._extract_name(url),
                            "article_count": len(articles),
                            "last_article": articles[0].title,
                            "relevance_score": relevance_score,
                            "reason": reason
                        })
                    else:
                         yield self._event("log", f"⚠️ Irrelevante: {url} (Score: {relevance_score} - {reason})")
                
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

    async def _generate_queries_with_llm(self, topic: str) -> list[str]:
        """Generate search queries using Gemini."""
        prompt = f"""Generate 4 distinct Google search queries to find high-quality news sources, blogs, or aggregators about: "{topic}".
        Include queries for specific niche sites, not just general news.
        If the topic implies a specific language (e.g., Spanish context), include queries in that language.
        Return ONLY the queries, one per line. No bullets, no numbering."""
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7)
            )
            queries = [q.strip() for q in response.text.split('\n') if q.strip()]
            return queries[:5]
        except Exception as e:
            print(f"LLM Error: {e}")
            return [f"{topic} news", f"best sites for {topic}"]

    def _check_frequency(self, articles: list) -> tuple[bool, str]:
        """Check if at least 1 article is from the last 90 days."""
        # Note: If published_at is None, we assume valid (optimistic)
        # In a real scenario, we might want to be stricter or try to parse date from text
        has_dates = False
        limit_date = datetime.now(UTC).replace(tzinfo=None)
        
        for art in articles:
            if art.published_at:
                has_dates = True
                # Naive check: is it within last 90 days?
                # Ensure tz-naive for comparison if simple string
                # Ideally published_at is a datetime object
                delta = (limit_date - art.published_at.replace(tzinfo=None)).days
                if delta < 90:
                    return True, art.published_at.isoformat()[:10]
        
        if not has_dates:
            # If we couldn't parse dates, fallback to True but warn
            return True, "Date unknown"
            
        return False, "Old content"

    async def _score_relevance(self, topic: str, articles: list) -> tuple[int, str]:
        """Score the relevance of the source based on article titles."""
        titles = [f"- {a.title} ({a.summary[:100]}...)" for a in articles[:5]]
        titles_text = "\n".join(titles)
        
        prompt = f"""Evaluate if this news source is relevant for the topic: "{topic}".
        
        Recent articles found:
        {titles_text}
        
        Give a relevance score from 0 to 10.
        7+ means it is a dedicated or highly relevant source.
        4-6 means it has some relevant content but mixed with other topics.
        0-3 means it is irrelevant or spam.
        
        Return JSON: {{"score": 8, "reason": "..."}}"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            import json
            data = json.loads(response.text)
            return data.get("score", 5), data.get("reason", "No reason provided")
        except Exception:
            return 10, "Error converting response"

    async def close(self):
        await self.search_service.close()
