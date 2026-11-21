"""Collection storage.

``CollectionRepository`` is the port; ``CollectionStore`` is the bounded in-memory
adapter used by default and in tests. ``infrastructure/sql_store.py`` provides the
SQLAlchemy adapter (SQLite locally, PostgreSQL in docker-compose and later RDS).
"""

from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import dataclass
from typing import Protocol

from moment_intelligence.domain.contracts import Consent, MomentCollectionResponse, Offer


@dataclass(frozen=True)
class StoredCollection:
    response: MomentCollectionResponse
    session_id: str
    consent: Consent

    def offer(self, offer_id: str) -> Offer | None:
        return next((o for o in self.response.offers if o.offer_id == offer_id), None)


class CollectionRepository(Protocol):
    def put(self, item: StoredCollection) -> None: ...

    def get(self, collection_id: str) -> StoredCollection | None: ...

    def status_counts(self) -> dict[str, int]: ...

    def offers_shown(self) -> int: ...


class CollectionStore:
    def __init__(self, max_items: int = 1_000) -> None:
        self._items: OrderedDict[str, StoredCollection] = OrderedDict()
        self._max = max_items

    def put(self, item: StoredCollection) -> None:
        self._items[item.response.collection_id] = item
        self._items.move_to_end(item.response.collection_id)
        while len(self._items) > self._max:
            self._items.popitem(last=False)

    def get(self, collection_id: str) -> StoredCollection | None:
        return self._items.get(collection_id)

    def status_counts(self) -> dict[str, int]:
        return dict(Counter(i.response.status for i in self._items.values()))

    def offers_shown(self) -> int:
        return sum(len(i.response.offers) for i in self._items.values())
