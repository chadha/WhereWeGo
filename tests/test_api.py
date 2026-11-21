from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import build_container, create_app
from conftest import FAKE_KEY, Recorder, make_tavily, ok
from moment_intelligence.core.config import Settings
from moment_intelligence.events.publisher import InMemoryEventPublisher
from moment_intelligence.providers.base import ProviderResult
from moment_intelligence.providers.mock import MockProvider
from moment_intelligence.providers.tavily import TavilyProvider

BODY: dict[str, Any] = {
    "request_id": "req_api_1",
    "session_id": "sess_api_1",
    "locale": "en-DE",
    "city": "Berlin",
    "companion": "partner",
    "desired_feelings": ["surprised", "connected"],
    "occasion": "date",
    "date_window": {"start": "2026-11-21", "end": "2026-11-22", "flexible": True},
    "budget": {"amount": 100, "currency": "EUR", "scope": "total"},
    "constraints": {"indoor_preferred": False, "max_travel_minutes": 45},
    "consent": {"analytics": True, "marketing": False},
}


def client_with(settings: Settings, provider: Any) -> tuple[TestClient, InMemoryEventPublisher]:
    publisher = InMemoryEventPublisher()
    container = build_container(settings=settings, provider=provider, publisher=publisher)
    return TestClient(create_app(container), follow_redirects=False), publisher


# ------------------------------------------------------------------ config switch


def test_mock_provider_used_without_credentials(no_key_settings: Settings) -> None:
    assert isinstance(build_container(settings=no_key_settings).provider, MockProvider)


def test_tavily_provider_used_with_credentials(settings: Settings) -> None:
    assert isinstance(build_container(settings=settings).provider, TavilyProvider)


# ---------------------------------------------------------- happy path (Tavily)


def test_discover_with_mocked_tavily(settings: Settings) -> None:
    rec = Recorder([ok()])
    client, publisher = client_with(settings, make_tavily(settings, rec))
    res = client.post("/v1/discover", json=BODY)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["data_source"] == "tavily_search"
    assert data["price_status"] == "unknown"
    assert data["availability_status"] == "not_verified"
    assert data["estimated_total"] is None
    assert 1 <= len(data["offers"]) <= 5
    ids = [o["offer_id"] for o in data["offers"]]
    assert len(ids) == len(set(ids))
    for o in data["offers"]:
        assert o["price"]["amount"] is None and o["price"]["price_scope"] == "unknown"
        assert o["availability_status"] == "unknown"
        assert o["affiliate_url"] is None
        assert o["source_url"].startswith("https://")
        assert o["provenance"]["retrieved_at"]
    assert [r["offer_id"] for r in data["explanation"]["ranking"]] == ids
    assert "within_budget" not in data["explanation"]["matched_preferences"]
    assert FAKE_KEY not in res.text
    assert publisher.types() == ["discovery_started", "discovery_completed"]
    assert rec.bodies[0]["max_results"] == 5


def test_offer_viewed_and_clicked_events_and_safe_redirect(settings: Settings) -> None:
    client, publisher = client_with(settings, make_tavily(settings, Recorder([ok()])))
    data = client.post("/v1/discover", json=BODY).json()
    col, offer = data["collection_id"], data["offers"][0]

    view = {
        "event_id": "evt_view_1",
        "event_type": "offer_viewed",
        "session_id": BODY["session_id"],
        "collection_id": col,
        "offer_id": offer["offer_id"],
    }
    assert client.post("/v1/events", json=view).json() == {"accepted": True, "recorded": True}
    # Idempotent: the same event_id is not recorded twice.
    assert client.post("/v1/events", json=view).json()["recorded"] is False

    go = client.get(
        f"/v1/offers/{offer['offer_id']}/go",
        params={"collection_id": col, "session_id": BODY["session_id"]},
    )
    assert go.status_code == 307
    assert go.headers["location"] == offer["source_url"]
    assert publisher.types() == [
        "discovery_started",
        "discovery_completed",
        "offer_viewed",
        "offer_clicked",
    ]


def test_redirect_and_events_reject_unknown_or_foreign_offers(settings: Settings) -> None:
    client, _ = client_with(settings, make_tavily(settings, Recorder([ok()])))
    data = client.post("/v1/discover", json=BODY).json()
    col = data["collection_id"]
    assert (
        client.get(
            "/v1/offers/web_fake/go",
            params={"collection_id": col, "session_id": BODY["session_id"]},
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/v1/offers/{data['offers'][0]['offer_id']}/go",
            params={"collection_id": col, "session_id": "other_session"},
        ).status_code
        == 404
    )
    bad = {
        "event_id": "evt_x",
        "event_type": "offer_clicked",
        "session_id": BODY["session_id"],
        "collection_id": col,
        "offer_id": "web_fake",
    }
    assert client.post("/v1/events", json=bad).status_code == 422
    server_only = dict(bad, event_type="discovery_completed")
    assert client.post("/v1/events", json=server_only).status_code == 422


def test_no_events_without_analytics_consent(settings: Settings) -> None:
    client, publisher = client_with(settings, make_tavily(settings, Recorder([ok()])))
    body = dict(BODY, consent={"analytics": False, "marketing": False})
    assert client.post("/v1/discover", json=body).status_code == 200
    assert publisher.events == [] and publisher.dropped_without_consent == 2


# --------------------------------------------------------------- safe fallbacks


@pytest.mark.parametrize(
    "responses,reason",
    [
        ([httpx.Response(503)], "search_unavailable"),
        ([httpx.ConnectTimeout("down")], "search_unavailable"),
        ([httpx.Response(401)], "search_failed"),
    ],
)
def test_provider_failures_return_honest_fallback(
    settings: Settings, responses: list[Any], reason: str
) -> None:
    client, publisher = client_with(settings, make_tavily(settings, Recorder(responses)))
    res = client.post("/v1/discover", json=BODY)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "degraded" and data["fallback_reason"] == reason
    assert data["offers"] == []
    assert FAKE_KEY not in res.text
    assert publisher.types() == ["discovery_started", "no_results_found", "discovery_completed"]


class SlowProvider:
    configuration = MockProvider.configuration

    async def search(self, query: Any) -> ProviderResult:
        await asyncio.sleep(5)
        raise AssertionError("unreachable")


class BrokenProvider:
    configuration = MockProvider.configuration

    async def search(self, query: Any) -> ProviderResult:
        raise RuntimeError("bug")


def test_overall_timeout_falls_back(settings: Settings) -> None:
    from dataclasses import replace

    client, _ = client_with(replace(settings, discovery_timeout_seconds=0.05), SlowProvider())
    data = client.post("/v1/discover", json=BODY).json()
    assert data["status"] == "degraded" and data["fallback_reason"] == "search_timeout"


def test_unexpected_provider_bug_falls_back(settings: Settings) -> None:
    client, _ = client_with(settings, BrokenProvider())
    data = client.post("/v1/discover", json=BODY).json()
    assert data["status"] == "degraded" and data["fallback_reason"] == "search_failed"


# ------------------------------------------------------------------- mock mode


def test_mock_mode_returns_labelled_illustrative_offers(no_key_settings: Settings) -> None:
    client, _ = client_with(no_key_settings, MockProvider())
    data = client.post("/v1/discover", json=BODY).json()
    assert data["status"] == "ok"
    assert data["data_source"] == "demo_catalogue" and data["price_status"] == "illustrative"
    assert all(o["is_illustrative"] for o in data["offers"])
    # Budget 100 total for a couple: 70 per person (140) and 120 total are excluded.
    titles = {o["title"] for o in data["offers"]}
    assert "Secret supper club" not in titles and "Escape room challenge" not in titles
    assert data["excluded_offers"] >= 2
    assert "within_budget" in data["explanation"]["matched_preferences"]
    # Demo offers have no external source, so there is nothing to redirect to.
    off = data["offers"][0]
    assert (
        client.get(
            f"/v1/offers/{off['offer_id']}/go",
            params={"collection_id": data["collection_id"], "session_id": BODY["session_id"]},
        ).status_code
        == 404
    )


def test_mock_mode_outside_berlin_has_no_results(no_key_settings: Settings) -> None:
    client, publisher = client_with(no_key_settings, MockProvider())
    data = client.post("/v1/discover", json=dict(BODY, city="Paris")).json()
    assert data["status"] == "no_results" and data["offers"] == []
    assert "no_results_found" in publisher.types()


# --------------------------------------------------------------- API hygiene


def test_validation_rate_limit_health_and_collection_lookup(settings: Settings) -> None:
    from dataclasses import replace

    client, _ = client_with(
        replace(settings, rate_limit_per_minute=2), make_tavily(settings, Recorder([ok()]))
    )
    assert client.post("/v1/discover", json=dict(BODY, budget={"amount": -1})).status_code == 422
    first = client.post("/v1/discover", json=BODY)
    assert client.post("/v1/discover", json=BODY).status_code == 200
    assert client.post("/v1/discover", json=BODY).status_code == 429
    ready = client.get("/v1/health/ready").json()
    assert ready["provider"] == "tavily" and FAKE_KEY not in str(ready)
    assert client.get("/v1/health/live").json() == {"status": "ok"}
    col = first.json()["collection_id"]
    assert client.get(f"/v1/collections/{col}").json()["collection_id"] == col
    assert client.get("/v1/collections/col_missing").status_code == 404
