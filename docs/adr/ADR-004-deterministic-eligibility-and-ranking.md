# ADR-004: Deterministic eligibility and ranking

**Status:** Accepted
**Date:** 2026-11-21

## Context
LLMs must not decide prices, budgets, availability, affiliate approval or legal eligibility.

## Decision
Eligibility checks (real offer, known price, price scope, companion, date, travel time, freshness, approved affiliate) and the initial weighted ranking are plain, tested code. Every offer keeps its score breakdown. No ML ranker in production until it beats this baseline on a held-out dataset and is approved.

## Consequences
Explainable, testable results and zero tolerance for budget violations. Ranking quality starts simple and improves through measured experiments.
