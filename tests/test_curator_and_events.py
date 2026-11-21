from __future__ import annotations

import asyncio
from typing import Any

from conftest import make_request
from moment_intelligence.agents.curator import curate
from moment_intelligence.agents.model_gateway import (
    BedrockModelGateway,
    GatewayDisabledError,
    MockModelGateway,
    build_gateway,
)
from moment_intelligence.core.config import Settings
from moment_intelligence.domain.contracts import Consent
from moment_intelligence.events.publisher import InMemoryEventPublisher, make_event


class FakeGateway:
    model_id = "fake"

    def __init__(self, proposal: dict[str, Any] | None, fail: bool = False) -> None:
        self.proposal, self.fail = proposal, fail

    async def generate_json(self, task: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        if self.fail:
            raise RuntimeError("model down")
        return self.proposal


def curate_with(gateway: Any) -> tuple[str, str, str]:
    return asyncio.run(curate(make_request(), gateway, is_demo=False))


def test_mock_gateway_uses_template() -> None:
    title, description, source = curate_with(MockModelGateway())
    assert source == "template" and title == "A night to remember"
    assert "not verified" in description


def test_valid_model_copy_is_used_and_keeps_honesty_note() -> None:
    title, description, source = curate_with(
        FakeGateway({"title": "Evening of small surprises", "description": "Quiet ideas."})
    )
    assert source == "model" and title == "Evening of small surprises"
    assert "not verified" in description


def test_model_copy_with_prices_links_or_claims_is_rejected() -> None:
    for bad in [
        {"title": "Dinner for 45 EUR", "description": "ok text"},
        {"title": "Fine title", "description": "Book at https://evil.example"},
        {"title": "Fine title", "description": "Your table is confirmed"},
        {"title": "Fine title", "description": "Tickets are available now"},
    ]:
        assert curate_with(FakeGateway(bad))[2] == "template"


def test_model_failure_falls_back_to_template() -> None:
    assert curate_with(FakeGateway(None, fail=True))[2] == "template"


def test_bedrock_stays_disabled_without_approval(settings: Settings) -> None:
    from dataclasses import replace

    assert isinstance(build_gateway(replace(settings, model_gateway="bedrock")), MockModelGateway)
    try:
        BedrockModelGateway(settings)
    except GatewayDisabledError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Bedrock must not start without BEDROCK_ENABLED=true")


def test_events_are_idempotent_and_consent_aware() -> None:
    pub = InMemoryEventPublisher()
    yes, no = Consent(analytics=True), Consent(analytics=False)
    event = make_event("offer_viewed", session_id="s1", consent=yes, event_id="evt_1")
    assert pub.publish(event) is True
    assert pub.publish(event) is False
    assert pub.publish(make_event("offer_viewed", session_id="s1", consent=no)) is False
    assert pub.types() == ["offer_viewed"] and pub.dropped_without_consent == 1
