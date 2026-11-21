"""Local demo catalogue used when no TAVILY_API_KEY is configured.

Every offer is marked ``is_illustrative=True`` and ``data_source="demo_catalogue"`` so it can
never be confused with live inventory. Demo prices are labelled illustrative in the response.
"""

from __future__ import annotations

from datetime import UTC, datetime

from moment_intelligence.domain.contracts import (
    Companion,
    Location,
    Offer,
    Price,
    Provenance,
    ProviderSearchQuery,
)
from moment_intelligence.providers.base import ProviderConfiguration, ProviderResult

PROVIDER_ID = "demo_catalogue"

# (slug, title, description, category, district, price, scope, suitable_for)
_CATALOGUE: list[tuple[str, str, str, str, str, float | None, str, list[Companion]]] = [
    (
        "pottery-evening",
        "Pottery evening for two",
        "Make something together at a wheel workshop, a relaxed and creative shared experience.",
        "creative_workshop",
        "Neukölln",
        45.0,
        "per_person",
        ["partner", "friends", "solo"],
    ),
    (
        "supper-club",
        "Secret supper club",
        "A surprise multi-course dinner at a hidden location, shared tables and new connections.",
        "food_experience",
        "Kreuzberg",
        70.0,
        "per_person",
        ["partner", "friends"],
    ),
    (
        "kayak-spree",
        "Sunset kayak on the Spree",
        "Paddle through the city at golden hour, an adventurous and calm way to see Berlin.",
        "adventure",
        "Friedrichshain",
        39.0,
        "per_person",
        ["partner", "friends", "family", "solo"],
    ),
    (
        "planetarium",
        "Planetarium night show",
        "An immersive dome show under the stars, indoor and family-friendly.",
        "culture",
        "Prenzlauer Berg",
        12.0,
        "per_person",
        ["family", "partner", "friends", "solo"],
    ),
    (
        "comedy-cellar",
        "English comedy cellar",
        "Stand-up night in an intimate basement club, laughter guaranteed.",
        "nightlife",
        "Mitte",
        18.0,
        "per_person",
        ["friends", "partner", "solo"],
    ),
    (
        "escape-room",
        "Escape room challenge",
        "Solve puzzles as a team against the clock, a fun surprise for groups.",
        "adventure",
        "Mitte",
        120.0,
        "total",
        ["friends", "family", "colleagues"],
    ),
]


class MockProvider:
    configuration = ProviderConfiguration(
        provider_id=PROVIDER_ID,
        enabled=True,
        kind="demo",
        requires_credentials=False,
        supports_search=True,
        supports_price=True,
        supports_availability=False,
        supports_affiliate_tracking=False,
    )

    async def search(self, query: ProviderSearchQuery) -> ProviderResult:
        now = datetime.now(UTC)
        offers = [
            Offer(
                offer_id=f"demo_{slug}",
                provider_id=PROVIDER_ID,
                title=title,
                description=desc,
                category=category,
                location=Location(city="Berlin", district=district),
                price=Price(amount=amount, currency="EUR", price_scope=scope),
                suitable_for=suitable,
                source_url=None,
                source_title=None,
                affiliate_url=None,
                availability_status="unknown",
                last_verified_at=None,
                data_source="demo_catalogue",
                is_illustrative=True,
                provenance=Provenance(
                    provider=PROVIDER_ID, retrieved_at=now, search_query=query.query
                ),
            )
            for slug, title, desc, category, district, amount, scope, suitable in _CATALOGUE
        ]
        # The demo catalogue only covers Berlin.
        if query.city.strip().lower() != "berlin":
            offers = []
        return ProviderResult(offers=offers, provider_id=PROVIDER_ID, raw_result_count=len(offers))
