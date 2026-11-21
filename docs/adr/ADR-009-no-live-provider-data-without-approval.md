# ADR-009: No live provider data without approval

**Status:** Accepted
**Date:** 2026-11-21

## Context
Visiting a provider site or the existence of an affiliate program does not grant rights to use its API or scrape its data.

## Decision
Ship a demo catalogue adapter first. Fever, Viator, Groupon, GetYourGuide and visitBerlin adapters exist as disabled skeletons and are enabled only after API access and the affiliate agreement are reviewed (`terms_reviewed_at`). No scraping. No fabricated affiliate URLs.

## Consequences
Legal and reputational safety. Live inventory arrives later than a scraped prototype would.
