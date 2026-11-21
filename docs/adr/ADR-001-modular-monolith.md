# ADR-001: Modular monolith before microservices

**Status:** Accepted
**Date:** 2026-11-21

## Context
We need production-grade structure from the start, but we have one team, one product and no operational evidence that forces independent deployment of components.

## Decision
Build a single deployable Python service with strict internal module boundaries (domain, application, agents, orchestration, providers, ranking, events, analytics, infrastructure). Do not create microservices without a demonstrated operational reason.

## Consequences
Simple deployment, testing and debugging. Boundaries keep a later split possible. Risk: boundaries erode without discipline, so module dependencies are reviewed and tested.
