"""Deterministic search planning: DiscoveryRequest -> ProviderSearchQuery.

No LLM is involved. The query contains only preferences the user actually sent.
"""

from __future__ import annotations

from datetime import date

from moment_intelligence.domain.contracts import DiscoveryRequest, ProviderSearchQuery

COMPANION_PHRASES: dict[str, str] = {
    "partner": "couples",
    "family": "families with kids",
    "friends": "groups of friends",
    "solo": "solo travellers",
    "colleagues": "teams and colleagues",
}

OCCASION_PHRASES: dict[str, str] = {
    "date": "date night ideas",
    "birthday": "birthday ideas",
    "anniversary": "anniversary ideas",
    "weekend": "weekend activities",
}


def _date_phrase(start: date, end: date) -> str:
    if start == end:
        return f"on {start.day} {start:%B %Y}"
    if start.month == end.month and start.year == end.year:
        return f"{start.day}-{end.day} {start:%B %Y}"
    return f"{start.day} {start:%B} - {end.day} {end:%B %Y}"


def build_search_query(request: DiscoveryRequest, max_results: int) -> ProviderSearchQuery:
    occasion = (request.occasion or "").lower()
    what = OCCASION_PHRASES.get(
        occasion, f"{occasion} experiences" if occasion else "unique experiences"
    )
    parts = [f"{what} in {request.city} for {COMPANION_PHRASES[request.companion]}"]
    if request.desired_feelings:
        parts.append(" and ".join(request.desired_feelings))
    if request.constraints.indoor_preferred:
        parts.append("indoor")
    if request.budget:
        per = " per person" if request.budget.scope == "per_person" else ""
        parts.append(f"under {request.budget.amount:g} EUR{per}")
    if request.date_window:
        parts.append(_date_phrase(request.date_window.start, request.date_window.end))
    query = ", ".join(parts)[:400]
    return ProviderSearchQuery(
        query=query, city=request.city, max_results=max(1, min(max_results, 5))
    )
