"""In-memory store for generated collections (local slice).

Replaced by PostgreSQL (ADR-005) in Phase 2. Bounded so it cannot grow without limit.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from moment_intelligence.domain.contracts import Consent, MomentCollectionResponse, Offer


@dataclass(frozen=True)
class StoredCollection:
    response: MomentCollectionResponse
    session_id: str
    consent: Consent

    def offer(self, offer_id: str) -> Offer | None:
        return next((o for o in self.response.offers if o.offer_id == offer_id), None)


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
