"""Consent-aware, idempotent behavioral event publishing (ADR-006, ADR-008).

Locally events are kept in memory. In AWS an SQS publisher implements the same
protocol (see infrastructure/). Events are only recorded with analytics consent.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Protocol

from moment_intelligence.domain.contracts import (
    BehavioralEvent,
    Consent,
    EventSource,
    EventType,
)


class EventPublisher(Protocol):
    def publish(self, event: BehavioralEvent) -> bool:
        """Return True if the event was recorded, False if dropped or duplicate."""
        ...


class EventStats(Protocol):
    """Optional read side used by the local demo summary."""

    dropped_without_consent: int

    def count_by_type(self) -> dict[str, int]: ...


class InMemoryEventPublisher:
    def __init__(self, max_events: int = 10_000) -> None:
        self._events: OrderedDict[str, BehavioralEvent] = OrderedDict()
        self._max = max_events
        self.dropped_without_consent = 0

    def publish(self, event: BehavioralEvent) -> bool:
        if not event.consent_state.analytics:
            self.dropped_without_consent += 1
            return False
        if event.event_id in self._events:
            return False  # idempotent
        self._events[event.event_id] = event
        while len(self._events) > self._max:
            self._events.popitem(last=False)
        return True

    @property
    def events(self) -> list[BehavioralEvent]:
        return list(self._events.values())

    def count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self._events.values():
            counts[e.event_type] = counts.get(e.event_type, 0) + 1
        return counts

    def types(self) -> list[str]:
        return [e.event_type for e in self._events.values()]


def make_event(
    event_type: EventType,
    *,
    session_id: str,
    consent: Consent,
    request_id: str | None = None,
    collection_id: str | None = None,
    offer_id: str | None = None,
    event_id: str | None = None,
    source: EventSource | None = None,
    properties: dict[str, str | int | float | bool | None] | None = None,
) -> BehavioralEvent:
    return BehavioralEvent(
        event_id=event_id or f"evt_{uuid.uuid4().hex}",
        event_type=event_type,
        occurred_at=datetime.now(UTC),
        session_id=session_id,
        request_id=request_id,
        collection_id=collection_id,
        offer_id=offer_id,
        source=source or EventSource(),
        consent_state=consent,
        properties=properties or {},
    )
