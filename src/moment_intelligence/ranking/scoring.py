"""Deterministic, explainable baseline ranking (ADR-004).

score = 0.30*intent_match + 0.25*budget_fit + 0.20*date_fit
        + 0.15*companion_fit + 0.10*source_confidence

Initial weights only; not claimed to be optimal. Unknown inputs score a neutral 0.5.
"""

from __future__ import annotations

import re

from moment_intelligence.domain.contracts import DiscoveryRequest, Offer, RankingExplanation
from moment_intelligence.ranking.eligibility import offer_total_for_budget

WEIGHTS = {
    "intent_match": 0.30,
    "budget_fit": 0.25,
    "date_fit": 0.20,
    "companion_fit": 0.15,
    "source_confidence": 0.10,
}
NEUTRAL = 0.5

SYNONYMS: dict[str, set[str]] = {
    "surprised": {"surprise", "surprising", "secret", "hidden", "unusual", "unexpected"},
    "connected": {"together", "shared", "connection", "couple", "couples", "intimate"},
    "relaxed": {"relax", "relaxed", "calm", "chill", "spa", "slow"},
    "adventurous": {"adventure", "adventurous", "outdoor", "kayak", "climbing"},
    "creative": {"creative", "workshop", "pottery", "painting", "craft"},
    "romantic": {"romantic", "romance", "candlelit", "couple", "couples"},
    "date": {"date", "romantic", "couple", "couples", "two"},
    "birthday": {"birthday", "party", "celebrate"},
}
COMPANION_TERMS: dict[str, set[str]] = {
    "partner": {"couple", "couples", "romantic", "date", "two"},
    "family": {"family", "families", "kids", "children", "child"},
    "friends": {"friends", "group", "groups", "team"},
    "solo": {"solo", "yourself", "alone"},
    "colleagues": {"team", "colleagues", "corporate", "group"},
}
_WORD = re.compile(r"[a-z0-9+]+")


def _words(offer: Offer) -> set[str]:
    return set(_WORD.findall(f"{offer.title} {offer.description} {offer.category}".lower()))


def intent_match(offer: Offer, request: DiscoveryRequest) -> float:
    groups = list(request.desired_feelings)
    if request.occasion:
        groups.append(request.occasion.lower())
    if not groups:
        return NEUTRAL
    words = _words(offer)
    hits = sum(1 for g in groups if (SYNONYMS.get(g, {g}) | {g}) & words)
    return hits / len(groups)


def budget_fit(offer: Offer, request: DiscoveryRequest) -> tuple[float, str | None]:
    if request.budget is None:
        return NEUTRAL, None
    total = offer_total_for_budget(offer, request)
    if total is None:
        return NEUTRAL, "price unknown or not comparable"
    # Eligibility already removed over-budget offers. Cheaper leaves more room.
    return 1.0 - 0.5 * (total / request.budget.amount), None


def companion_fit(offer: Offer, request: DiscoveryRequest) -> float:
    if offer.suitable_for:
        return 1.0 if request.companion in offer.suitable_for else 0.0
    return 1.0 if COMPANION_TERMS[request.companion] & _words(offer) else NEUTRAL


def source_confidence(offer: Offer) -> float:
    score = offer.provenance.relevance_score
    return NEUTRAL if score is None else max(0.0, min(1.0, score))


def explain(offer: Offer, request: DiscoveryRequest) -> RankingExplanation:
    notes: list[str] = []
    im = intent_match(offer, request)
    bf, note = budget_fit(offer, request)
    if note:
        notes.append(note)
    df = NEUTRAL
    if request.date_window:
        notes.append("date not verified")
    cf = companion_fit(offer, request)
    sc = source_confidence(offer)
    score = (
        WEIGHTS["intent_match"] * im
        + WEIGHTS["budget_fit"] * bf
        + WEIGHTS["date_fit"] * df
        + WEIGHTS["companion_fit"] * cf
        + WEIGHTS["source_confidence"] * sc
    )
    return RankingExplanation(
        offer_id=offer.offer_id,
        score=round(score, 4),
        intent_match=round(im, 4),
        budget_fit=round(bf, 4),
        date_fit=round(df, 4),
        companion_fit=round(cf, 4),
        source_confidence=round(sc, 4),
        notes=notes,
    )


def rank(offers: list[Offer], request: DiscoveryRequest) -> list[tuple[Offer, RankingExplanation]]:
    scored = [(o, explain(o, request)) for o in offers]
    # Deterministic: score desc, then offer_id for stable tie-breaking.
    scored.sort(key=lambda pair: (-pair[1].score, pair[0].offer_id))
    return scored
