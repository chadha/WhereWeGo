"""Versioned data contracts (single source of truth).

See docs/data-contracts.md. Unknown values are always explicit: a price we do not
know is ``None`` with ``price_scope="unknown"``; availability we did not verify is
``"unknown"``. Nothing here may be represented as confirmed without a trusted source.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

SCHEMA_VERSION: Literal["1.0"] = "1.0"

Companion = Literal["partner", "family", "friends", "solo", "colleagues"]
PriceScope = Literal["per_person", "total", "unknown"]
AvailabilityStatus = Literal["available", "unavailable", "unknown"]
DataSource = Literal["tavily_search", "demo_catalogue", "provider_api"]
EventType = Literal[
    "discovery_started",
    "preferences_submitted",
    "discovery_completed",
    "collection_viewed",
    "offer_viewed",
    "offer_clicked",
    "no_results_found",
    "affiliate_conversion_confirmed",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---------------------------------------------------------------- DiscoveryRequest


class DateWindow(_Strict):
    start: date
    end: date
    flexible: bool = False

    @model_validator(mode="after")
    def _ordered(self) -> DateWindow:
        if self.end < self.start:
            raise ValueError("date_window.end must not be before date_window.start")
        if (self.end - self.start).days > 31:
            raise ValueError("date_window may span at most 31 days")
        return self


class Budget(_Strict):
    amount: float = Field(gt=0, le=10_000)
    currency: Literal["EUR"] = "EUR"
    scope: Literal["per_person", "total"] = "total"


class Constraints(_Strict):
    indoor_preferred: bool = False
    max_travel_minutes: int | None = Field(default=None, ge=5, le=240)


class Consent(_Strict):
    analytics: bool = False
    marketing: bool = False


class DiscoveryRequest(_Strict):
    request_id: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_\-\.]+$")
    session_id: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_\-\.]+$")
    locale: str = Field(default="en-DE", pattern=r"^[a-z]{2}-[A-Z]{2}$")
    city: str = Field(min_length=2, max_length=60, pattern=r"^[\w .'\-]+$")
    companion: Companion
    desired_feelings: list[str] = Field(default_factory=list, max_length=5)
    occasion: str | None = Field(default=None, max_length=40, pattern=r"^[\w .'\-]+$")
    date_window: DateWindow | None = None
    budget: Budget | None = None
    constraints: Constraints = Field(default_factory=Constraints)
    consent: Consent = Field(default_factory=Consent)
    schema_version: Literal["1.0"] = SCHEMA_VERSION

    @field_validator("desired_feelings")
    @classmethod
    def _clean_feelings(cls, v: list[str]) -> list[str]:
        cleaned = []
        for item in v:
            item = item.strip().lower()
            if not item or len(item) > 30 or not item.replace(" ", "").replace("-", "").isalpha():
                raise ValueError("desired_feelings must be short words")
            cleaned.append(item)
        return cleaned


# --------------------------------------------------------------------------- Offer


class Location(_Strict):
    city: str | None = None
    district: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class Price(_Strict):
    amount: float | None = None
    currency: Literal["EUR"] | None = None
    price_scope: PriceScope = "unknown"

    @model_validator(mode="after")
    def _consistent(self) -> Price:
        if self.amount is None and self.price_scope != "unknown":
            raise ValueError("an unknown price must have price_scope 'unknown'")
        if self.amount is not None and (self.currency is None or self.price_scope == "unknown"):
            raise ValueError("a known price needs a currency and a price scope")
        return self


class Provenance(_Strict):
    """Where an offer came from and how we found it."""

    provider: str
    retrieved_at: datetime
    search_query: str | None = None
    search_depth: str | None = None
    relevance_score: float | None = None


class Offer(_Strict):
    offer_id: str
    provider_id: str
    title: str
    description: str
    category: str = "unknown"
    location: Location = Field(default_factory=Location)
    price: Price = Field(default_factory=Price)
    suitable_for: list[Companion] = Field(default_factory=list)
    source_url: HttpUrl | None = None
    source_title: str | None = None
    affiliate_url: HttpUrl | None = None
    availability_status: AvailabilityStatus = "unknown"
    last_verified_at: datetime | None = None
    data_source: DataSource
    is_illustrative: bool
    provenance: Provenance
    schema_version: Literal["1.0"] = SCHEMA_VERSION


class ProviderSearchQuery(_Strict):
    query: str = Field(min_length=3, max_length=400)
    city: str
    max_results: int = Field(ge=1, le=5)
    search_depth: Literal["basic"] = "basic"


# ---------------------------------------------------------------------- Ranking


class RankingExplanation(_Strict):
    offer_id: str
    score: float
    intent_match: float
    budget_fit: float
    date_fit: float
    companion_fit: float
    source_confidence: float
    notes: list[str] = Field(default_factory=list)


class EligibilityDecision(_Strict):
    offer_id: str
    eligible: bool
    reasons: list[str] = Field(default_factory=list)


# ------------------------------------------------------- MomentCollectionResponse


class CollectionExplanation(_Strict):
    matched_preferences: list[str] = Field(default_factory=list)
    ranking: list[RankingExplanation] = Field(default_factory=list)


class MomentCollectionResponse(_Strict):
    collection_id: str
    request_id: str
    title: str
    description: str
    currency: Literal["EUR"] = "EUR"
    estimated_total: float | None = None
    price_status: Literal["unknown", "illustrative", "estimated", "verified"]
    offers: list[Offer]
    explanation: CollectionExplanation
    availability_status: Literal["not_verified", "verified"] = "not_verified"
    status: Literal["ok", "no_results", "degraded"]
    fallback_reason: str | None = None
    data_source: DataSource
    excluded_offers: int = 0
    generated_at: datetime
    schema_version: Literal["1.0"] = SCHEMA_VERSION


# ----------------------------------------------------------------- BehavioralEvent


class EventSource(_Strict):
    channel: str | None = None
    utm_source: str | None = Field(default=None, max_length=100)
    utm_medium: str | None = Field(default=None, max_length=100)
    utm_campaign: str | None = Field(default=None, max_length=100)
    referrer_domain: str | None = Field(default=None, max_length=200)


class BehavioralEvent(_Strict):
    event_id: str = Field(min_length=3, max_length=64)
    event_type: EventType
    occurred_at: datetime
    session_id: str
    request_id: str | None = None
    collection_id: str | None = None
    offer_id: str | None = None
    source: EventSource = Field(default_factory=EventSource)
    consent_state: Consent
    properties: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    schema_version: Literal["1.0"] = SCHEMA_VERSION


class ClientEventRequest(_Strict):
    """Events the frontend may send. Server-side events are emitted by the API itself."""

    event_id: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_\-\.]+$")
    event_type: Literal["offer_viewed", "offer_clicked", "collection_viewed"]
    session_id: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_\-\.]+$")
    collection_id: str
    offer_id: str | None = None
    source: EventSource = Field(default_factory=EventSource)
