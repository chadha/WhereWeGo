"""Tavily Search adapter.

Tavily is a web search API, not a booking catalogue. Its results are web pages about
experiences. We therefore:
- keep the page URL and title as provenance (never as a booking or affiliate URL),
- never derive prices, availability or provider confirmation from them,
- request ``search_depth="basic"`` explicitly (1 credit) and at most five results.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import httpx

from moment_intelligence.core.config import MAX_SEARCH_RESULTS, Settings
from moment_intelligence.core.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    PermanentProviderError,
    RetryStats,
    TransientProviderError,
    call_with_retries,
)
from moment_intelligence.domain.contracts import Location, Offer, Provenance, ProviderSearchQuery
from moment_intelligence.providers.base import ProviderConfiguration, ProviderResult
from moment_intelligence.providers.normalization import (
    clean_text,
    deduplicate,
    is_safe_public_url,
    stable_offer_id,
)

PROVIDER_ID = "tavily"


class TavilyProvider:
    configuration = ProviderConfiguration(
        provider_id=PROVIDER_ID,
        enabled=True,
        kind="web_search",
        requires_credentials=True,
        supports_search=True,
        supports_price=False,
        supports_availability=False,
        supports_affiliate_tracking=False,
    )

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
        breaker: CircuitBreaker | None = None,
        retry_base_delay_seconds: float = 0.25,
    ) -> None:
        if settings.tavily_api_key is None:
            raise ValueError("TavilyProvider requires TAVILY_API_KEY")
        self._settings = settings
        self._client = client or httpx.AsyncClient(base_url=settings.tavily_base_url)
        self._breaker = breaker or CircuitBreaker()
        self._retry_base_delay = retry_base_delay_seconds

    async def aclose(self) -> None:
        await self._client.aclose()

    def _payload(self, query: ProviderSearchQuery) -> dict[str, Any]:
        return {
            "query": query.query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": min(
                query.max_results, self._settings.tavily_max_results, MAX_SEARCH_RESULTS
            ),
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }

    async def _request(self, query: ProviderSearchQuery) -> dict[str, Any]:
        key = self._settings.tavily_api_key
        assert key is not None
        try:
            response = await self._client.post(
                "/search",
                json=self._payload(query),
                headers={"Authorization": f"Bearer {key.get_secret_value()}"},
                timeout=self._settings.tavily_timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise TransientProviderError(type(exc).__name__) from None
        if response.status_code == 429 or response.status_code >= 500:
            raise TransientProviderError(f"tavily status {response.status_code}")
        if response.status_code >= 400:
            # 400/401/403/432/433: do not retry; never include the key in the message.
            raise PermanentProviderError(f"tavily status {response.status_code}")
        try:
            data = response.json()
        except ValueError:
            raise PermanentProviderError("tavily returned invalid JSON") from None
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise PermanentProviderError("tavily response missing results")
        return data

    async def search(self, query: ProviderSearchQuery) -> ProviderResult:
        if self._breaker.is_open:
            raise CircuitOpenError(PROVIDER_ID)
        stats = RetryStats()
        started = time.perf_counter()
        try:
            data = await call_with_retries(
                lambda: self._request(query),
                max_retries=self._settings.tavily_max_retries,
                base_delay_seconds=self._retry_base_delay,
                stats=stats,
            )
        except (TransientProviderError, PermanentProviderError):
            self._breaker.record_failure()
            raise
        self._breaker.record_success()
        retrieved_at = datetime.now(UTC)
        raw = data["results"][:MAX_SEARCH_RESULTS]
        offers = [o for o in (self._normalize(r, query, retrieved_at) for r in raw) if o]
        offers, removed = deduplicate(offers)
        return ProviderResult(
            offers=offers,
            provider_id=PROVIDER_ID,
            attempts=stats.attempts,
            retries=stats.retries,
            latency_ms=int((time.perf_counter() - started) * 1000),
            raw_result_count=len(raw),
            duplicates_removed=removed,
        )

    @staticmethod
    def _normalize(result: Any, query: ProviderSearchQuery, retrieved_at: datetime) -> Offer | None:
        """Map one Tavily result to an Offer. Unknown stays unknown."""
        if not isinstance(result, dict):
            return None
        url = result.get("url")
        if not isinstance(url, str) or not is_safe_public_url(url):
            return None
        title = clean_text(str(result.get("title") or ""), 160)
        if not title:
            return None
        score = result.get("score")
        relevance = float(score) if isinstance(score, (int, float)) else None
        if relevance is not None:
            relevance = max(0.0, min(1.0, relevance))
        return Offer(
            offer_id=stable_offer_id("web", url),
            provider_id=PROVIDER_ID,
            title=title,
            description=clean_text(str(result.get("content") or ""), 400),
            category="web_result",
            # The page was found by searching this city; it is not a verified venue location.
            location=Location(city=None),
            # Price and availability are unknown: Tavily does not provide them.
            source_url=url,
            source_title=title,
            affiliate_url=None,
            availability_status="unknown",
            last_verified_at=None,
            data_source="tavily_search",
            is_illustrative=False,
            provenance=Provenance(
                provider=PROVIDER_ID,
                retrieved_at=retrieved_at,
                search_query=query.query,
                search_depth=query.search_depth,
                relevance_score=relevance,
            ),
        )
