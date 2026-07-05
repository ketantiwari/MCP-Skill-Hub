from __future__ import annotations

from dataclasses import dataclass

import httpx

from dynamic_mcp_skill_hub.config import get_settings


@dataclass(frozen=True)
class ResearchResult:
    title: str
    url: str
    summary: str


class TavilyResearchAdapter:
    def search(self, query: str) -> list[ResearchResult]:
        settings = get_settings()
        if not settings.tavily_api_key:
            return []
        try:
            response = httpx.post(
                "https://api.tavily.com/search",
                headers={"Content-Type": "application/json"},
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 5,
                    "include_answer": False,
                    "include_raw_content": False,
                },
                timeout=settings.model_timeout_ms / 1000,
            )
            response.raise_for_status()
            data = response.json()
            results = []
            for item in data.get("results", []):
                results.append(
                    ResearchResult(
                        title=str(item.get("title", "")),
                        url=str(item.get("url", "")),
                        summary=str(item.get("content", "")),
                    )
                )
            return results
        except Exception:
            return []
