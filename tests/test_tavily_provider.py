from __future__ import annotations

import asyncio

import httpx
import pytest

from conftest import FAKE_KEY, Recorder, make_request, make_tavily, ok, tavily_result
from moment_intelligence.application.query_builder import build_search_query
from moment_intelligence.core.config import Settings
from moment_intelligence.core.resilience import (
    CircuitOpenError,
    PermanentProviderError,
    TransientProviderError,
)


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def query():  # type: ignore[no-untyped-def]
    return build_search_query(make_request(), max_results=5)


def test_request_uses_basic_depth_bearer_auth_and_max_five(settings: Settings) -> None:
    rec = Recorder([ok()])
    run(make_tavily(settings, rec).search(query()))
    req = rec.requests[0]
    body = rec.bodies[0]
    assert req.url.path == "/search"
    assert req.headers["authorization"] == f"Bearer {FAKE_KEY}"
    assert body["search_depth"] == "basic"
    assert body["max_results"] == 5
    assert body["include_answer"] is False and body["include_raw_content"] is False
    assert "api_key" not in body


def test_results_capped_at_five_deduplicated_and_unsafe_urls_dropped(settings: Settings) -> None:
    result = run(make_tavily(settings, Recorder([ok()])).search(query()))
    urls = [str(o.source_url) for o in result.offers]
    assert result.raw_result_count == 5  # 7 returned, only the first 5 considered
    assert result.duplicates_removed == 1
    assert len(result.offers) == 3
    assert not any("127.0.0.1" in u or u.startswith("javascript") for u in urls)
    assert all("seventh" not in u for u in urls)


def test_normalization_never_invents_price_availability_or_booking(settings: Settings) -> None:
    result = run(make_tavily(settings, Recorder([ok()])).search(query()))
    pottery = next(o for o in result.offers if "Pottery" in o.title)
    supper = next(o for o in result.offers if "supper" in o.title.lower())
    for offer in result.offers:
        assert offer.price.amount is None and offer.price.price_scope == "unknown"
        assert offer.availability_status == "unknown"  # even if the page says "available"
        assert offer.affiliate_url is None
        assert offer.last_verified_at is None
        assert offer.is_illustrative is False and offer.data_source == "tavily_search"
        assert offer.provenance.provider == "tavily"
        assert offer.provenance.retrieved_at is not None
        assert offer.provenance.search_query
        assert offer.source_title == offer.title
    # "from 70 EUR" in the snippet is NOT turned into a price.
    assert supper.price.amount is None
    assert str(pottery.source_url) == "https://pottery.example.com/date-night"


def test_retries_transient_errors_then_succeeds(settings: Settings) -> None:
    rec = Recorder([httpx.Response(503), httpx.ReadTimeout("slow"), ok()])
    result = run(make_tavily(settings, rec).search(query()))
    assert len(rec.requests) == 3
    assert result.attempts == 3 and result.retries == 2


def test_retries_are_bounded(settings: Settings) -> None:
    rec = Recorder([httpx.Response(500)])
    with pytest.raises(TransientProviderError):
        run(make_tavily(settings, rec).search(query()))
    assert len(rec.requests) == 3  # 1 attempt + max 2 retries


@pytest.mark.parametrize("status", [400, 401, 403, 432])
def test_permanent_errors_are_not_retried_and_hide_the_key(settings: Settings, status: int) -> None:
    rec = Recorder([httpx.Response(status, json={"detail": "nope"})])
    with pytest.raises(PermanentProviderError) as err:
        run(make_tavily(settings, rec).search(query()))
    assert len(rec.requests) == 1
    assert FAKE_KEY not in str(err.value)


def test_malformed_payload_is_permanent(settings: Settings) -> None:
    rec = Recorder([httpx.Response(200, json={"unexpected": True})])
    with pytest.raises(PermanentProviderError):
        run(make_tavily(settings, rec).search(query()))


def test_circuit_breaker_opens_after_repeated_failures(settings: Settings) -> None:
    rec = Recorder([httpx.Response(401)])
    provider = make_tavily(settings, rec)
    for _ in range(5):
        with pytest.raises(PermanentProviderError):
            run(provider.search(query()))
    with pytest.raises(CircuitOpenError):
        run(provider.search(query()))
    assert len(rec.requests) == 5  # the 6th call never reached Tavily


def test_garbage_results_are_skipped(settings: Settings) -> None:
    results = [
        {"no": "url"},
        tavily_result("https://ok.example.com", ""),
        tavily_result("https://good.example.com/a", "Good one"),
    ]
    result = run(make_tavily(settings, Recorder([ok(results)])).search(query()))
    assert [o.title for o in result.offers] == ["Good one"]
