"""Affiliate link building and the tracked redirect (ADR-013).

All partner hosts and IDs here are fake test values on reserved example domains.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from app.main import build_container, create_app
from conftest import Recorder, make_tavily, ok
from moment_intelligence.core.affiliate import (
    AffiliateConfigError,
    AffiliateRule,
    build_affiliate_url,
    parse_affiliate_rules,
)
from moment_intelligence.core.config import Settings, load_settings
from moment_intelligence.events.publisher import InMemoryEventPublisher
from test_api import BODY

RULES = (AffiliateRule("example.com", (("partner_id", "TESTPID"),), "cmp"),)
RULES_JSON = (
    '[{"domain": "example.com", "params": {"partner_id": "TESTPID"}, "click_id_param": "cmp"}]'
)


def query(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(url).query)


# ------------------------------------------------------------------ link builder


def test_no_rules_means_no_affiliate_link() -> None:
    assert build_affiliate_url("https://www.example.com/tour", ()) is None


def test_partner_host_and_subdomains_are_tagged_with_click_id() -> None:
    for url in ("https://example.com/tour", "https://pottery.example.com/date-night?x=1"):
        tagged = build_affiliate_url(url, RULES, "clk_abc123")
        assert tagged is not None
        assert urlsplit(tagged).hostname == urlsplit(url).hostname
        assert urlsplit(tagged).path == urlsplit(url).path
        assert query(tagged)["partner_id"] == ["TESTPID"]
        assert query(tagged)["cmp"] == ["clk_abc123"]
    assert query(build_affiliate_url("https://a.example.com/t?x=1", RULES) or "")["x"] == ["1"]


def test_other_hosts_and_lookalikes_are_never_tagged() -> None:
    for url in (
        "https://blog.example.org/unusual-berlin",
        "https://notexample.com/tour",
        "https://example.com.evil.test/tour",
        "http://example.com/tour",  # not https
        "https://user:pw@example.com/tour",
        "javascript:alert(1)",
        "",
        None,
    ):
        assert build_affiliate_url(url, RULES, "clk_1") is None


def test_foreign_partner_ids_in_the_source_url_are_replaced() -> None:
    tagged = build_affiliate_url(
        "https://example.com/tour?partner_id=SOMEONE_ELSE&cmp=theirs&keep=1", RULES, "clk_1"
    )
    assert tagged is not None
    assert query(tagged) == {"keep": ["1"], "partner_id": ["TESTPID"], "cmp": ["clk_1"]}
    assert "SOMEONE_ELSE" not in tagged


def test_unsafe_click_id_is_dropped_but_link_is_still_tagged() -> None:
    tagged = build_affiliate_url("https://example.com/tour", RULES, "bad id&x=1")
    assert tagged is not None and query(tagged) == {"partner_id": ["TESTPID"]}


# ------------------------------------------------------------------ configuration


def test_rules_parse_from_json_and_empty_means_disabled() -> None:
    assert parse_affiliate_rules(None) == ()
    assert parse_affiliate_rules("  ") == ()
    assert parse_affiliate_rules(RULES_JSON) == RULES
    www = parse_affiliate_rules('[{"domain": "WWW.Example.com", "params": {"a": "b"}}]')
    assert www == (AffiliateRule("example.com", (("a", "b"),), None),)


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        '{"domain": "example.com"}',
        '[{"domain": "example.com"}]',
        '[{"domain": "example.com", "params": {}}]',
        '[{"domain": "https://example.com/x", "params": {"a": "b"}}]',
        '[{"domain": "localhost", "params": {"a": "b"}}]',
        '[{"domain": "example.com", "params": {"a b": "c"}}]',
        '[{"domain": "example.com", "params": {"a": "b&c=d"}}]',
        '[{"domain": "example.com", "params": {"a": 1}}]',
        '[{"domain": "example.com", "params": {"a": "b"}, "click_id_param": "a"}]',
        '[{"domain": "example.com", "params": {"a": "b"}, "extra": 1}]',
        '[{"domain": "example.com", "params": {"a": "b"}},'
        ' {"domain": "example.com", "params": {"a": "c"}}]',
    ],
)
def test_malformed_rules_fail_loudly_without_echoing_values(raw: str) -> None:
    with pytest.raises(AffiliateConfigError) as err:
        parse_affiliate_rules(raw)
    assert "b&c=d" not in str(err.value)


def test_settings_load_rules_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AFFILIATE_RULES", raising=False)
    assert load_settings().affiliate_rules == ()
    monkeypatch.setenv("AFFILIATE_RULES", RULES_JSON)
    assert load_settings().affiliate_rules == RULES


# ------------------------------------------------------------------ /go redirect


def client_with(settings: Settings) -> tuple[TestClient, InMemoryEventPublisher]:
    publisher = InMemoryEventPublisher()
    provider = make_tavily(settings, Recorder([ok()]))
    container = build_container(settings=settings, provider=provider, publisher=publisher)
    return TestClient(create_app(container), follow_redirects=False), publisher


def discover(client: TestClient) -> tuple[str, dict[str, Any], dict[str, Any]]:
    data = client.post("/v1/discover", json=BODY).json()
    partner = next(o for o in data["offers"] if "example.com" in o["source_url"])
    other = next(o for o in data["offers"] if "example.com" not in o["source_url"])
    return data["collection_id"], partner, other


def go(client: TestClient, col: str, offer: dict[str, Any], session: str) -> Any:
    return client.get(
        f"/v1/offers/{offer['offer_id']}/go",
        params={"collection_id": col, "session_id": session},
    )


def test_go_without_rules_redirects_to_plain_source_url(settings: Settings) -> None:
    client, publisher = client_with(settings)
    col, partner, _ = discover(client)
    res = go(client, col, partner, BODY["session_id"])
    assert res.status_code == 307 and res.headers["location"] == partner["source_url"]
    click = publisher.events[-1]
    assert click.event_type == "offer_clicked" and click.properties["monetised"] is False
    assert client.get("/v1/health/ready").json()["affiliate_links"] is False


def test_go_tags_partner_offers_only_and_records_click_id(settings: Settings) -> None:
    client, publisher = client_with(replace(settings, affiliate_rules=RULES))
    col, partner, other = discover(client)

    res = go(client, col, partner, BODY["session_id"])
    assert res.status_code == 307
    location = res.headers["location"]
    assert location.split("?")[0] == partner["source_url"].split("?")[0]
    assert query(location)["partner_id"] == ["TESTPID"]
    click = publisher.events[-1]
    assert click.properties["monetised"] is True
    assert query(location)["cmp"] == [click.properties["click_id"]]

    plain = go(client, col, other, BODY["session_id"])
    assert plain.status_code == 307 and plain.headers["location"] == other["source_url"]
    assert publisher.events[-1].properties["monetised"] is False
    assert client.get("/v1/health/ready").json()["affiliate_links"] is True


def test_offers_in_the_api_response_never_carry_an_affiliate_url(settings: Settings) -> None:
    client, _ = client_with(replace(settings, affiliate_rules=RULES))
    data = client.post("/v1/discover", json=BODY).json()
    assert data["offers"] and all(o["affiliate_url"] is None for o in data["offers"])
    assert "TESTPID" not in str(data)


def test_friend_session_is_redirected_but_not_recorded(settings: Settings) -> None:
    client, publisher = client_with(replace(settings, affiliate_rules=RULES))
    col, partner, _ = discover(client)
    before = len(publisher.events)
    res = go(client, col, partner, "sess_friend_2")
    assert res.status_code == 307
    assert query(res.headers["location"])["partner_id"] == ["TESTPID"]
    # The friend never gave analytics consent, so nothing is stored for their session.
    assert len(publisher.events) == before
    assert publisher.dropped_without_consent == 1
