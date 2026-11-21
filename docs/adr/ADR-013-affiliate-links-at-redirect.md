# ADR-013: Affiliate links are added only at the redirect, from approved rules

**Status:** Proposed
**Date:** 2026-11-21

## Context
The business model is affiliate commission: a partner pays when a click from WhereWeGo ends in a completed booking. Until now `/go` redirected to the plain source URL, so no click could earn, and it rejected every session except the one that created the collection, so a friend who joined by link could not reach the offer. We must add revenue without weakening the rules that no link is invented (ADR-004) and no partner is used before approval (ADR-009).

## Decision
- Offers never carry an affiliate URL. `Offer.affiliate_url` stays empty and the existing eligibility and output checks that reject it stay in place.
- The link is tagged at one place only, the `/go` redirect, by deterministic code in `core/affiliate.py`. The destination is always the stored source URL; the code only adds query parameters.
- A link is tagged only when its host is an https host of a partner listed in `AFFILIATE_RULES`. A human adds a rule after the programme has accepted us and its terms are reviewed. The default is empty, which means nothing is tagged and behaviour is unchanged.
- Parameter names and IDs come from the partner dashboard through configuration. Parameters of the same name already in a URL are replaced, so a web result cannot pass someone else's partner ID through our redirect.
- Each click gets a random `click_id`, sent to the partner as its sub-ID where the rule names one and stored on the `offer_clicked` event with `monetised: true/false`. It is not derived from the session.
- `/go` accepts any session for a valid collection and offer. The stored consent belongs to the organiser's session, so a click from another session is redirected but not recorded (ADR-008).
- Commission is not an input to eligibility or ranking.

## Consequences
Clicks on partner pages can earn as soon as one partner is approved and configured, with no code change. Web-search results earn only when they happen to be partner pages, so meaningful revenue still needs partner catalogue adapters (issue #5). Friends' clicks are not counted until the frontend collects their consent. Bookings are still unknown to us: `affiliate_conversion_confirmed` needs an import of partner reports, matched by `click_id`. The frontend must show a commission notice before a partner is switched on.
