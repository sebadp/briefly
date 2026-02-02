"""Research Agent for finding and validating news sources with streaming capabilities."""

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any, TypedDict, cast

from app.agents import get_scraper_agent
from app.config import get_settings
from app.services.search_service import SearchService

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai: Any = None  # type: ignore[no-redef]


class ResearchState(TypedDict):
    topic: str
    found_sources: list[dict[str, Any]]
    attempted_queries: list[str]
    steps_taken: int
    max_steps: int


class ResearchAgent:
    """
    Agent that performs deep research to find news sources for a topic.
    Designed for streaming output of its thought process.
    """

    def __init__(self) -> None:
        self.search_service = SearchService()
        self.settings = get_settings()

        # Initialize Gemini if available
        self.client = None
        if self.settings.gemini_api_key and genai:
            self.client = genai.Client(api_key=self.settings.gemini_api_key)
            self.model = "gemini-2.0-flash"

    async def research_topic(
        self, topic: str, user_settings: dict[str, Any] | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Research a topic and yield streaming events.
        Events are JSON strings in SSE format.

        Args:
            topic: The topic to research
            user_settings: Optional user settings dict with:
                - articles_per_source: int (default 5)
                - max_sources_per_briefing: int (default 8)
                - min_relevance_score: int (default 7)
                - language: str (default "es")
        """
        # Apply user settings with defaults
        settings_config = user_settings or {}
        articles_per_source = settings_config.get("articles_per_source", 5)
        max_sources = settings_config.get("max_sources_per_briefing", 8)
        min_relevance = settings_config.get("min_relevance_score", 7)
        language = settings_config.get("language", "es")

        try:
            # ReAct Loop
            # ReAct Loop
            state: ResearchState = {
                "topic": topic,
                "found_sources": [],
                "attempted_queries": [],
                "steps_taken": 0,
                "max_steps": 5,
            }

            scraper = get_scraper_agent()

            while state["steps_taken"] < state["max_steps"]:
                state["steps_taken"] += 1
                step = state["steps_taken"]

                # 1. THOUGHT: Decide next action
                yield self._event(
                    "log", f"🤔 Paso {step}/{state['max_steps']}: Analizando próximo paso..."
                )

                decision = await self._decide_next_step(state)
                action = decision.get("action", "FINISH")
                reason = decision.get("reason", "")

                if action == "FINISH":
                    if not state["found_sources"]:
                        yield self._event(
                            "log", "⚠️ No se encontraron fuentes, pero el agente decidió terminar."
                        )
                    else:
                        yield self._event("log", f"🏁 Decisión: Terminar investigación. ({reason})")
                    break

                # 2. ACT: Search
                query = decision.get("query")
                if isinstance(query, str):
                    state["attempted_queries"].append(query)
                yield self._event("log", f"🚀 Acción: Buscar '{query}' ({reason})")

                results = await self.search_service.search(
                    str(query), num_results=articles_per_source
                )

                # Filter seen domains
                new_candidates = []
                # Collect all previously seen domains from state
                seen_domains = {s["url"] for s in state["found_sources"]}  # Simplified check

                for res in results:
                    link = res.get("link")
                    if link:
                        domain = self._extract_base_url(link)
                        # We use a simple check, in a real DB we'd check globally
                        if domain and domain not in seen_domains:
                            new_candidates.append(
                                {"base": domain, "full": link, "title": res.get("title")}
                            )
                            seen_domains.add(domain)  # Mark as seen for this loop

                if not new_candidates:
                    yield self._event(
                        "log", "⚠️ No se encontraron nuevos candidatos en esta búsqueda."
                    )
                    continue

                # 3. OBSERVE: Validate
                yield self._event(
                    "log", f"⚡ Validando {len(new_candidates)} nuevos candidatos (Stream)..."
                )

                tasks = [
                    self._validate_candidate(
                        scraper, cand, topic, min_relevance, articles_per_source, language
                    )
                    for cand in new_candidates
                ]

                added_count = 0
                for future in asyncio.as_completed(tasks):
                    validation_res = await future
                    if validation_res:
                        yield self._event("log", validation_res["log_msg"])
                        if validation_res.get("valid"):
                            source_data = validation_res.get("source_data")
                            if isinstance(source_data, dict):
                                state["found_sources"].append(cast(dict[str, Any], source_data))
                            added_count += 1

                yield self._event(
                    "log", f"📈 Progreso: {len(state['found_sources'])} fuentes válidas acumuladas."
                )

                # Early stop if we have enough sources
                if len(state["found_sources"]) >= max_sources:
                    yield self._event(
                        "log", f"🎉 Meta alcanzada ({max_sources}+ fuentes). Terminando."
                    )
                    break

            await scraper.close()

            # 4. Final Result
            valid_sources = state["found_sources"]

            # 4. Final Result
            if valid_sources:
                yield self._event(
                    "log", f"🎉 Investigación completada. {len(valid_sources)} fuentes encontradas."
                )
                yield self._event(
                    "result",
                    {
                        "topic": topic,
                        "sources": valid_sources,
                        "created_at": datetime.now(UTC).isoformat(),
                    },
                )
            else:
                yield self._event(
                    "log",
                    "😓 No se encontraron fuentes válidas que pudieran ser scrapeadas automáticamente.",
                )
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

        """
        # Removed _generate_queries_with_llm as it is replaced by _decide_next_step
        """
        pass

    def _check_frequency(self, articles: list[Any]) -> tuple[bool, str]:
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

    async def _decide_next_step(self, state: ResearchState) -> dict[str, Any]:
        """Decide next action: SEARCH more or FINISH."""
        # Heuristic fallback if no LLM
        if not self.client:
            if not state["attempted_queries"]:
                return {"action": "SEARCH", "query": f"best news sites {state['topic']}"}
            if len(state["found_sources"]) < 3 and state["steps_taken"] < 2:
                return {"action": "SEARCH", "query": f"{state['topic']} news analysis"}
            return {"action": "FINISH", "reason": "Heuristic limit"}

        sources_summary = "\n".join(
            [f"- {s['name']} (Score: {s.get('relevance_score')})" for s in state["found_sources"]]
        )

        prompt = f"""You are a Research Agent.
        Topic: "{state["topic"]}"
        Current Progress: {len(state["found_sources"])} valid sources found.
        Sources:
        {sources_summary}

        Previous Queries: {state["attempted_queries"]}
        Steps Taken: {state["steps_taken"]}/{state["max_steps"]}

        Decide the next step.
        - If we have 5+ high quality sources, typically FINISH.
        - If we have few sources, SEARCH with a NEW, distinct query.
        - If we tried many queries and found nothing, FINISH.

        Return JSON: {{"action": "SEARCH", "query": "new query here", "reason": "why"}}
        OR {{"action": "FINISH", "reason": "why"}}"""

        try:
            if self.client:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
                if response.text:
                    import json

                    return dict(json.loads(response.text))
                return {"action": "FINISH", "reason": "Empty AI response"}
            return {"action": "FINISH", "reason": "No AI client"}
        except Exception as e:
            print(f"Decision Error: {e}")
            return {"action": "FINISH", "reason": "Error in decision logic"}

    async def _score_relevance(self, topic: str, articles: list[Any]) -> tuple[int, str]:
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
            if self.client:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
                if response.text:
                    import json

                    data = json.loads(response.text)
                    return data.get("score", 5), data.get("reason", "No reason provided")
            return 5, "No AI client"
        except Exception:
            return 10, "Error converting response"

    async def _validate_candidate(
        self,
        scraper: Any,
        cand: dict[str, Any],
        topic: str,
        min_relevance: int = 7,
        articles_per_source: int = 5,
        language: str = "es",
    ) -> dict[str, Any] | None:
        """Validate a single candidate source. Returns dict with result or None if error."""
        _ = language  # Reserved for future prompt localization
        url = cand["base"]
        try:
            # Quick validation scrape
            articles = await scraper.scrape_multiple_from_homepage(url, limit=articles_per_source)

            if not articles or len(articles) == 0:
                return {
                    "valid": False,
                    "log_msg": f"⚠️ Descartado: {url} (Sin artículos accesibles)",
                }

            # Validation 1: Frequency Check
            valid_freq, last_date = self._check_frequency(articles)
            if not valid_freq:
                return {
                    "valid": False,
                    "log_msg": f"🕰️ Descartado: {url} (Inactivo, último artículo: {last_date})",
                }

            # Validation 2: Relevance Score (LLM)
            relevance_score, reason = 10, "Heuristic pass"
            if self.client:
                relevance_score, reason = await self._score_relevance(topic, articles)

            # Validation 3: Check for RSS (Optional bonus)
            rss_url = None
            if hasattr(scraper, "detect_rss_feed"):
                rss_url = await scraper.detect_rss_feed(url)

            if relevance_score >= min_relevance:
                return {
                    "valid": True,
                    "log_msg": f"✨ Válido: {url} (Score: {relevance_score}/10, RSS: {'✅' if rss_url else '❌'})",
                    "source_data": {
                        "url": url,
                        "name": cand["title"] or self._extract_name(url),
                        "article_count": len(articles),
                        "last_article": articles[0].title,
                        "relevance_score": relevance_score,
                        "reason": reason,
                        "rss_url": rss_url,
                    },
                }
            else:
                return {
                    "valid": False,
                    "log_msg": f"⚠️ Irrelevante: {url} (Score: {relevance_score} - {reason})",
                }

        except Exception:
            return {"valid": False, "log_msg": f"❌ Error accediendo a {url}"}

    async def close(self) -> None:
        await self.search_service.close()
