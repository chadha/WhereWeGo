# ADR-012: Tavily as a web-search provider

**Status:** Accepted
**Date:** 2026-11-21

## Context
Provider catalogue APIs (Fever, Viator, GetYourGuide, visitBerlin) need agreements before we can use them (ADR-009). We still want real, current results for Berlin discovery. Tavily Search is a web search API built for agents, and the repository owner approved its use with their own API key.

## Decision
Integrate Tavily through a dedicated `TavilyProvider` adapter that implements the common provider interface, declared as `kind="web_search"`:
- Used only when `TAVILY_API_KEY` is set; otherwise the demo catalogue is used. Tests always mock Tavily.
- `search_depth="basic"` and at most five results per discovery, to bound cost (1 credit per basic search).
- Results are web pages, not bookable offers: they are normalized into `Offer` with full provenance, and price, availability, provider confirmation and booking/affiliate URLs are always left unknown/empty.
- Timeouts, at most two retries on transient errors, a circuit breaker, and a safe fallback.
- Web results and demo data are never mixed in one collection.

## Consequences
Real, sourced ideas without provider agreements, at a bounded cost. Users must click through to the source to check prices and availability; the response says so. Live, bookable inventory still requires approved catalogue adapters.
