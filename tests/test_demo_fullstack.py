"""End-to-end tests of the exact local demo journey the frontend performs."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import build_container, create_app
from conftest import FAKE_KEY, Recorder, make_tavily, ok
from moment_intelligence.core.config import Settings
from moment_intelligence.infrastructure.sql_store import SqlEventPublisher, make_engine
from moment_intelligence.providers.mock import MockProvider
from test_api import BODY


def sql_client(settings: Settings, db: Path, provider: Any) -> TestClient:
    s = replace(settings, database_url=f"sqlite:///{db}", cors_origins=("http://localhost:8080",))
    return TestClient(
        create_app(build_container(settings=s, provider=provider)), follow_redirects=False
    )


def journey(client: TestClient, body: dict[str, Any]) -> dict[str, Any]:
    """health -> discover -> collection_viewed -> offer_viewed -> click."""
    assert client.get("/v1/health/ready").status_code == 200
    data = client.post("/v1/discover", json=body).json()
    col, sess = data["collection_id"], body["session_id"]
    client.post(
        "/v1/events",
        json={
            "event_id": f"evt_cv_{col}",
            "event_type": "collection_viewed",
            "session_id": sess,
            "collection_id": col,
        },
    )
    for o in data["offers"]:
        client.post(
            "/v1/events",
            json={
                "event_id": f"evt_ov_{o['offer_id']}",
                "event_type": "offer_viewed",
                "session_id": sess,
                "collection_id": col,
                "offer_id": o["offer_id"],
            },
        )
    return data


def test_live_search_journey_persists_and_summarizes(settings: Settings, tmp_path: Path) -> None:
    db = tmp_path / "demo.db"
    client = sql_client(settings, db, make_tavily(settings, Recorder([ok()])))
    data = journey(client, BODY)
    first = data["offers"][0]
    go = client.get(
        f"/v1/offers/{first['offer_id']}/go",
        params={"collection_id": data["collection_id"], "session_id": BODY["session_id"]},
    )
    assert go.status_code == 307 and go.headers["location"] == first["source_url"]

    summary = client.get("/v1/demo/summary").json()
    assert summary["provider"] == "tavily"
    assert summary["discoveries"] == 1 and summary["ok"] == 1
    assert summary["offers_shown"] == len(data["offers"])
    assert summary["offer_views"] == len(data["offers"])
    assert summary["offer_clicks"] == 1
    assert summary["click_through_rate"] == round(1 / len(data["offers"]), 4)
    assert FAKE_KEY not in str(summary)

    # A restarted API (new container, same database) still knows the collection.
    restarted = sql_client(settings, db, MockProvider())
    again = restarted.get(f"/v1/collections/{data['collection_id']}")
    assert again.status_code == 200 and again.json()["offers"] == data["offers"]
    assert restarted.get("/v1/demo/summary").json()["offer_clicks"] == 1


def test_offline_demo_journey_without_key(no_key_settings: Settings, tmp_path: Path) -> None:
    client = sql_client(no_key_settings, tmp_path / "offline.db", MockProvider())
    data = journey(client, BODY)
    assert data["status"] == "ok" and data["data_source"] == "demo_catalogue"
    assert client.get("/v1/demo/summary").json()["provider"] == "demo_catalogue"


def test_sql_publisher_is_idempotent_and_consent_aware(tmp_path: Path) -> None:
    from moment_intelligence.domain.contracts import Consent
    from moment_intelligence.events.publisher import make_event

    pub = SqlEventPublisher(make_engine(f"sqlite:///{tmp_path / 'e.db'}"))
    e = make_event(
        "offer_viewed", session_id="s", consent=Consent(analytics=True), event_id="evt_same"
    )
    assert pub.publish(e) is True and pub.publish(e) is False
    assert pub.publish(make_event("offer_viewed", session_id="s", consent=Consent())) is False
    assert pub.count_by_type() == {"offer_viewed": 1} and pub.dropped_without_consent == 1


def test_cors_allows_only_configured_local_frontend(settings: Settings, tmp_path: Path) -> None:
    client = sql_client(settings, tmp_path / "c.db", MockProvider())
    headers = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    allowed = client.options("/v1/discover", headers={**headers, "Origin": "http://localhost:8080"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:8080"
    denied = client.options("/v1/discover", headers={**headers, "Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in denied.headers


def test_demo_summary_can_be_disabled(settings: Settings) -> None:
    s = replace(settings, demo_summary_enabled=False)
    client = TestClient(create_app(build_container(settings=s, provider=MockProvider())))
    assert client.get("/v1/demo/summary").status_code == 404
