"""FastAPI application: the local discovery vertical slice.

Run:  uvicorn app.main:app --app-dir apps/api --reload
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from moment_intelligence.agents.model_gateway import ModelGateway, build_gateway
from moment_intelligence.application.collection_store import (
    CollectionRepository,
    CollectionStore,
)
from moment_intelligence.application.demo_summary import DemoSummary, build_summary
from moment_intelligence.application.discovery import DiscoveryService
from moment_intelligence.core.config import Settings, load_settings
from moment_intelligence.core.rate_limit import RateLimiter
from moment_intelligence.domain.contracts import (
    ClientEventRequest,
    DiscoveryRequest,
    MomentCollectionResponse,
    Offer,
)
from moment_intelligence.events.publisher import (
    EventPublisher,
    InMemoryEventPublisher,
    make_event,
)
from moment_intelligence.infrastructure.sql_store import (
    SqlCollectionStore,
    SqlEventPublisher,
    make_engine,
)
from moment_intelligence.providers.base import ExperienceProvider
from moment_intelligence.providers.mock import MockProvider
from moment_intelligence.providers.normalization import is_safe_public_url
from moment_intelligence.providers.tavily import TavilyProvider

logging.basicConfig(level=logging.INFO)


@dataclass
class Container:
    settings: Settings
    provider: ExperienceProvider
    gateway: ModelGateway
    publisher: EventPublisher
    store: CollectionRepository
    discovery: DiscoveryService
    limiter: RateLimiter


def build_container(
    settings: Settings | None = None,
    provider: ExperienceProvider | None = None,
    publisher: EventPublisher | None = None,
    gateway: ModelGateway | None = None,
) -> Container:
    settings = settings or load_settings()
    if provider is None:
        provider = TavilyProvider(settings) if settings.use_tavily else MockProvider()
    gateway = gateway or build_gateway(settings)
    store: CollectionRepository
    if settings.database_url:
        engine = make_engine(settings.database_url)
        store = SqlCollectionStore(engine)
        publisher = publisher or SqlEventPublisher(engine)
    else:
        store = CollectionStore()
        publisher = publisher or InMemoryEventPublisher()
    discovery = DiscoveryService(
        provider, gateway, publisher, store, timeout_seconds=settings.discovery_timeout_seconds
    )
    return Container(
        settings,
        provider,
        gateway,
        publisher,
        store,
        discovery,
        RateLimiter(settings.rate_limit_per_minute),
    )


def create_app(container: Container | None = None) -> FastAPI:
    c = container or build_container()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        aclose = getattr(c.provider, "aclose", None)
        if aclose is not None:
            await aclose()

    app = FastAPI(title="Moment Intelligence API", version="0.1.0", lifespan=lifespan)
    app.state.container = c
    if c.settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(c.settings.cors_origins),
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
            allow_credentials=False,
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, __: Exception) -> JSONResponse:
        # Never leak internals or secrets.
        return JSONResponse(status_code=500, content={"detail": "internal_error"})

    @app.get("/v1/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/health/ready")
    async def ready() -> dict[str, str | bool]:
        cfg = c.provider.configuration
        return {
            "status": "ok",
            "provider": cfg.provider_id,
            "provider_kind": cfg.kind,
            "model_gateway": c.gateway.model_id,
            "live_search": cfg.kind == "web_search",
        }

    @app.get("/v1/demo/summary", response_model=DemoSummary)
    async def demo_summary() -> DemoSummary:
        """Aggregate local demo numbers. Disable with DEMO_SUMMARY_ENABLED=false outside demos."""
        if not c.settings.demo_summary_enabled:
            raise HTTPException(status_code=404, detail="not_found")
        return build_summary(c.provider.configuration.provider_id, c.store, c.publisher)

    @app.post("/v1/discover", response_model=MomentCollectionResponse)
    async def discover(body: DiscoveryRequest, request: Request) -> MomentCollectionResponse:
        client = request.client.host if request.client else "unknown"
        if not c.limiter.allow(f"{client}:{body.session_id}"):
            raise HTTPException(status_code=429, detail="rate_limited")
        return await c.discovery.discover(body)

    @app.get("/v1/collections/{collection_id}", response_model=MomentCollectionResponse)
    async def get_collection(collection_id: str) -> MomentCollectionResponse:
        stored = c.store.get(collection_id)
        if stored is None:
            raise HTTPException(status_code=404, detail="collection_not_found")
        return stored.response

    @app.get("/v1/offers/{offer_id}", response_model=Offer)
    async def get_offer(offer_id: str, collection_id: str = Query(...)) -> Offer:
        stored = c.store.get(collection_id)
        offer = stored.offer(offer_id) if stored else None
        if offer is None:
            raise HTTPException(status_code=404, detail="offer_not_found")
        return offer

    @app.post("/v1/events", status_code=202)
    async def record_event(body: ClientEventRequest) -> dict[str, bool]:
        stored = c.store.get(body.collection_id)
        if stored is None or stored.session_id != body.session_id:
            raise HTTPException(status_code=404, detail="collection_not_found")
        needs_offer = body.event_type in ("offer_viewed", "offer_clicked")
        if needs_offer and (not body.offer_id or stored.offer(body.offer_id) is None):
            raise HTTPException(status_code=422, detail="offer_not_in_collection")
        recorded = c.publisher.publish(
            make_event(
                body.event_type,
                event_id=body.event_id,
                session_id=body.session_id,
                consent=stored.consent,
                request_id=stored.response.request_id,
                collection_id=body.collection_id,
                offer_id=body.offer_id,
                source=body.source,
            )
        )
        return {"accepted": True, "recorded": recorded}

    @app.get("/v1/offers/{offer_id}/go")
    async def go_to_offer(
        offer_id: str, collection_id: str = Query(...), session_id: str = Query(...)
    ) -> RedirectResponse:
        """Record offer_clicked and redirect to the stored source URL (no open redirect)."""
        stored = c.store.get(collection_id)
        offer = stored.offer(offer_id) if stored and stored.session_id == session_id else None
        if offer is None or stored is None:
            raise HTTPException(status_code=404, detail="offer_not_found")
        url = str(offer.source_url) if offer.source_url else None
        if not is_safe_public_url(url):
            raise HTTPException(status_code=404, detail="no_external_source")
        c.publisher.publish(
            make_event(
                "offer_clicked",
                session_id=session_id,
                consent=stored.consent,
                request_id=stored.response.request_id,
                collection_id=collection_id,
                offer_id=offer_id,
                properties={"via": "redirect"},
            )
        )
        assert url is not None
        return RedirectResponse(url=url, status_code=307)

    return app


app = create_app()
