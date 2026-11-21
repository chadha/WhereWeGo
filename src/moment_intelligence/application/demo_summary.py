"""Aggregate numbers for the local demo / pitch slide. No per-user data."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from moment_intelligence.application.collection_store import CollectionRepository


class DemoSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    discoveries: int
    ok: int
    no_results: int
    degraded: int
    offers_shown: int
    offer_views: int
    offer_clicks: int
    click_through_rate: float | None
    events_recorded: int
    events_dropped_without_consent: int
    note: str
    generated_at: datetime


def build_summary(provider: str, store: CollectionRepository, publisher: Any) -> DemoSummary:
    statuses = store.status_counts()
    by_type: dict[str, int] = (
        publisher.count_by_type() if hasattr(publisher, "count_by_type") else {}
    )
    views = by_type.get("offer_viewed", 0)
    clicks = by_type.get("offer_clicked", 0)
    return DemoSummary(
        provider=provider,
        discoveries=sum(statuses.values()),
        ok=statuses.get("ok", 0),
        no_results=statuses.get("no_results", 0),
        degraded=statuses.get("degraded", 0),
        offers_shown=store.offers_shown(),
        offer_views=views,
        offer_clicks=clicks,
        click_through_rate=round(clicks / views, 4) if views else None,
        events_recorded=sum(by_type.values()),
        events_dropped_without_consent=int(getattr(publisher, "dropped_without_consent", 0)),
        note="Views and clicks only count sessions that gave analytics consent. "
        "Clicks are not bookings.",
        generated_at=datetime.now(UTC),
    )
