"""Deterministic eligibility checks, applied in the documented order (architecture §5C).

Unknown price/date/travel data does not exclude an offer; it is passed through and
explained. Known violations (over budget, wrong companion, unsafe URL, stale source,
unapproved affiliate link) exclude the offer.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from moment_intelligence.domain.contracts import DiscoveryRequest, EligibilityDecision, Offer
from moment_intelligence.providers.normalization import is_safe_public_url

MAX_SOURCE_AGE = timedelta(hours=24)
APPROVED_AFFILIATE_DOMAINS: frozenset[str] = frozenset()  # none approved yet (ADR-009)
_ADULTS_ONLY = re.compile(r"\b(18\+|adults[- ]only|over 18s?|ab 18)\b", re.I)

# Party sizes we can state without guessing. Family/friends/colleagues are unknown.
KNOWN_PARTY_SIZE = {"partner": 2, "solo": 1}


def offer_total_for_budget(offer: Offer, request: DiscoveryRequest) -> float | None:
    """Convert an offer price into the budget's scope. ``None`` when that is not knowable."""
    if offer.price.amount is None or request.budget is None:
        return None
    if offer.price.price_scope == request.budget.scope:
        return offer.price.amount
    size = KNOWN_PARTY_SIZE.get(request.companion)
    if size is None:
        return None
    if offer.price.price_scope == "per_person" and request.budget.scope == "total":
        return offer.price.amount * size
    if offer.price.price_scope == "total" and request.budget.scope == "per_person":
        return offer.price.amount / size
    return None


def check_eligibility(
    offer: Offer, request: DiscoveryRequest, now: datetime | None = None
) -> EligibilityDecision:
    now = now or datetime.now(UTC)
    reasons: list[str] = []
    eligible = True

    # 1. Real and permitted to display.
    if offer.data_source == "tavily_search" and not is_safe_public_url(
        str(offer.source_url) if offer.source_url else None
    ):
        return EligibilityDecision(
            offer_id=offer.offer_id, eligible=False, reasons=["unsafe_or_missing_source_url"]
        )
    if offer.data_source == "demo_catalogue" and not offer.is_illustrative:
        return EligibilityDecision(
            offer_id=offer.offer_id, eligible=False, reasons=["demo_offer_not_marked_illustrative"]
        )

    # 2 + 3. Price known and compatible with budget; scope understood.
    total = offer_total_for_budget(offer, request)
    if offer.price.amount is None:
        reasons.append("price_unknown")
    elif total is None:
        reasons.append("price_scope_not_comparable")
    elif request.budget is not None and total > request.budget.amount:
        eligible = False
        reasons.append("over_budget")

    # 4. Companion suitability.
    if offer.suitable_for and request.companion not in offer.suitable_for:
        eligible = False
        reasons.append("not_suitable_for_companion")
    if request.companion == "family" and _ADULTS_ONLY.search(f"{offer.title} {offer.description}"):
        eligible = False
        reasons.append("adults_only")

    # 5 + 6. Date and travel constraints: providers give no data yet.
    if request.date_window:
        reasons.append("date_not_verified")
    if request.constraints.max_travel_minutes:
        reasons.append("travel_time_not_verified")

    # 7. Freshness.
    age = now - offer.provenance.retrieved_at
    if offer.data_source == "tavily_search" and age > MAX_SOURCE_AGE:
        eligible = False
        reasons.append("stale_source")

    # 8. Affiliate destination approved.
    if offer.affiliate_url is not None:
        host = (urlsplit(str(offer.affiliate_url)).hostname or "").lower()
        if host not in APPROVED_AFFILIATE_DOMAINS:
            eligible = False
            reasons.append("unapproved_affiliate_url")

    return EligibilityDecision(offer_id=offer.offer_id, eligible=eligible, reasons=reasons)
