"""Discovery workflow: a controlled, bounded sequence (architecture §5).

validate -> plan query -> provider search (timeout, retries, breaker) -> normalize/dedupe
-> eligibility -> ranking -> curator -> output validation -> store -> events.

Any provider failure produces a safe, honest fallback response instead of an error page.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import UTC, datetime

from moment_intelligence.agents.curator import curate
from moment_intelligence.agents.model_gateway import ModelGateway
from moment_intelligence.application.collection_store import (
    CollectionRepository,
    StoredCollection,
)
from moment_intelligence.application.query_builder import build_search_query
from moment_intelligence.core.resilience import (
    CircuitOpenError,
    PermanentProviderError,
    TransientProviderError,
)
from moment_intelligence.domain.contracts import (
    CollectionExplanation,
    DiscoveryRequest,
    MomentCollectionResponse,
    Offer,
)
from moment_intelligence.events.publisher import EventPublisher, make_event
from moment_intelligence.providers.base import ExperienceProvider, ProviderResult
from moment_intelligence.providers.normalization import deduplicate, is_safe_public_url
from moment_intelligence.ranking.eligibility import check_eligibility, offer_total_for_budget
from moment_intelligence.ranking.scoring import rank

log = logging.getLogger("moment_intelligence.discovery")

MAX_OFFERS_IN_COLLECTION = 5


class OutputValidationError(Exception):
    pass


def validate_collection(collection: MomentCollectionResponse, provider_offer_ids: set[str]) -> None:
    """Reject hallucinated offers, unknown prices claimed as known, or unsafe links."""
    for offer in collection.offers:
        if offer.offer_id not in provider_offer_ids:
            raise OutputValidationError(f"offer {offer.offer_id} not returned by provider")
        if offer.affiliate_url is not None:
            raise OutputValidationError("affiliate links are not approved")
        if offer.source_url is not None and not is_safe_public_url(str(offer.source_url)):
            raise OutputValidationError("unsafe source url")
        if offer.data_source == "tavily_search" and (
            offer.price.amount is not None or offer.availability_status != "unknown"
        ):
            raise OutputValidationError("web results cannot carry prices or availability")
    if collection.price_status == "verified" or collection.availability_status == "verified":
        raise OutputValidationError("nothing is verified in this slice")


class DiscoveryService:
    def __init__(
        self,
        provider: ExperienceProvider,
        gateway: ModelGateway,
        publisher: EventPublisher,
        store: CollectionRepository,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.provider = provider
        self.gateway = gateway
        self.publisher = publisher
        self.store = store
        self.timeout_seconds = timeout_seconds

    async def discover(self, request: DiscoveryRequest) -> MomentCollectionResponse:
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        started = time.perf_counter()
        provider_id = self.provider.configuration.provider_id
        is_demo = self.provider.configuration.kind == "demo"
        self.publisher.publish(
            make_event(
                "discovery_started",
                session_id=request.session_id,
                consent=request.consent,
                request_id=request.request_id,
                properties={"provider": provider_id},
            )
        )

        query = build_search_query(request, max_results=5)
        result: ProviderResult | None = None
        fallback_reason: str | None = None
        try:
            result = await asyncio.wait_for(self.provider.search(query), self.timeout_seconds)
        except TimeoutError:
            fallback_reason = "search_timeout"
        except CircuitOpenError:
            fallback_reason = "search_temporarily_unavailable"
        except TransientProviderError:
            fallback_reason = "search_unavailable"
        except PermanentProviderError:
            fallback_reason = "search_failed"
        except Exception:  # noqa: BLE001 - never let a provider bug take the site down
            log.exception("provider_unexpected_error", extra={"provider": provider_id})
            fallback_reason = "search_failed"

        offers: list[Offer] = result.offers if result else []
        offers, _ = deduplicate(offers)
        decisions = [check_eligibility(o, request) for o in offers]
        eligible = [o for o, d in zip(offers, decisions, strict=True) if d.eligible]
        ranked = rank(eligible, request)[:MAX_OFFERS_IN_COLLECTION]
        chosen = [o for o, _ in ranked]

        title, description, copy_source = await curate(request, self.gateway, is_demo)
        status = "degraded" if fallback_reason else ("ok" if chosen else "no_results")
        if fallback_reason:
            title, description = (
                "We couldn't search right now",
                "Our search provider did not respond. No ideas are shown rather than "
                "made-up ones. Please try again in a moment.",
            )
        collection = MomentCollectionResponse(
            collection_id=f"col_{uuid.uuid4().hex[:16]}",
            request_id=request.request_id,
            title=title,
            description=description,
            estimated_total=None,
            price_status="illustrative" if is_demo else "unknown",
            offers=chosen,
            explanation=CollectionExplanation(
                matched_preferences=self._matched_preferences(request, chosen),
                ranking=[r for _, r in ranked],
            ),
            status=status,
            fallback_reason=fallback_reason,
            data_source="demo_catalogue" if is_demo else "tavily_search",
            excluded_offers=len(offers) - len(eligible),
            generated_at=datetime.now(UTC),
        )
        try:
            validate_collection(collection, {o.offer_id for o in offers})
            validation = "passed"
        except OutputValidationError:
            validation = "failed"
            collection = collection.model_copy(
                update={
                    "offers": [],
                    "status": "degraded",
                    "fallback_reason": "validation_failed",
                    "explanation": CollectionExplanation(),
                }
            )

        self.store.put(StoredCollection(collection, request.session_id, request.consent))
        props: dict[str, str | int | float | bool | None] = {
            "provider": provider_id,
            "status": collection.status,
            "offer_count": len(collection.offers),
            "fallback_reason": collection.fallback_reason,
        }
        if not collection.offers:
            self.publisher.publish(
                make_event(
                    "no_results_found",
                    session_id=request.session_id,
                    consent=request.consent,
                    request_id=request.request_id,
                    collection_id=collection.collection_id,
                    properties=props,
                )
            )
        self.publisher.publish(
            make_event(
                "discovery_completed",
                session_id=request.session_id,
                consent=request.consent,
                request_id=request.request_id,
                collection_id=collection.collection_id,
                properties=props,
            )
        )
        # Structured trace without personal data or secrets.
        trace = {
            "request_id": request.request_id,
            "workflow_id": workflow_id,
            "model_id": self.gateway.model_id,
            "copy_source": copy_source,
            "provider": provider_id,
            "attempts": result.attempts if result else None,
            "retries": result.retries if result else None,
            "provider_latency_ms": result.latency_ms if result else None,
            "raw_results": result.raw_result_count if result else 0,
            "duplicates_removed": result.duplicates_removed if result else 0,
            "excluded": collection.excluded_offers,
            "fallback": collection.fallback_reason,
            "validation": validation,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
        log.info("discovery_trace %s", json.dumps(trace, default=str))
        return collection

    @staticmethod
    def _matched_preferences(request: DiscoveryRequest, offers: list[Offer]) -> list[str]:
        if not offers:
            return []
        matched = list(request.desired_feelings) + [request.companion]
        totals = [offer_total_for_budget(o, request) for o in offers]
        if request.budget and totals and all(t is not None for t in totals):
            matched.append("within_budget")
        return matched
