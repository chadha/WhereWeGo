"""Moment Curator: writes the collection title and description.

The curator may only phrase things. It never adds offers, prices, availability or links.
A model may propose wording through the gateway; the proposal is validated and rejected
if it mentions prices, URLs or booking claims. Otherwise a deterministic template is used.
"""

from __future__ import annotations

import re

from moment_intelligence.agents.model_gateway import ModelGateway
from moment_intelligence.domain.contracts import DiscoveryRequest

TITLES = {
    "partner": "A night to remember",
    "family": "Family moments",
    "friends": "Good times with friends",
    "solo": "Time for yourself",
    "colleagues": "Team moments",
}
_FORBIDDEN = re.compile(
    r"(https?://|www\.|€|\beur\b|\$|\d+[.,]?\d*\s*(euro|eur)|\bbooked\b|\bconfirmed\b|"
    r"\bavailable\b|\bguaranteed\b)",
    re.I,
)


def template_copy(request: DiscoveryRequest, is_demo: bool) -> tuple[str, str]:
    title = TITLES[request.companion]
    feelings = " and ".join(request.desired_feelings) or "memorable"
    if is_demo:
        description = (
            f"Illustrative demo ideas in {request.city} for a {feelings} moment. "
            "These are sample experiences, not live offers."
        )
    else:
        description = (
            f"Ideas we found for {request.city} that match a {feelings} moment. "
            "Prices and availability are not verified: please check each source."
        )
    return title, description


def _valid(text: object, max_len: int) -> bool:
    return isinstance(text, str) and 3 <= len(text) <= max_len and not _FORBIDDEN.search(text)


async def curate(
    request: DiscoveryRequest, gateway: ModelGateway, is_demo: bool
) -> tuple[str, str, str]:
    """Return (title, description, source) where source is 'model' or 'template'."""
    title, description = template_copy(request, is_demo)
    try:
        proposal = await gateway.generate_json(
            "moment_curator_copy",
            {
                "companion": request.companion,
                "feelings": request.desired_feelings,
                "city": request.city,
            },
        )
    except Exception:  # noqa: BLE001 - the LLM may fail without failing discovery
        proposal = None
    if proposal and _valid(proposal.get("title"), 80) and _valid(proposal.get("description"), 280):
        # Keep our honesty note even when the model phrases the description.
        note = template_copy(request, is_demo)[1].split(". ", 1)[1]
        return str(proposal["title"]), f"{proposal['description']} {note}", "model"
    return title, description, "template"
