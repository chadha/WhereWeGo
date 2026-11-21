# ADR-005: PostgreSQL as operational source of truth

**Status:** Accepted
**Date:** 2026-11-21

## Context
Providers, offers, prices, locations, categories and affiliate status have clear relational structure.

## Decision
Use Amazon RDS for PostgreSQL with SQLAlchemy and Alembic migrations. No graph or vector database at the start.

## Consequences
Mature, well-understood store with strong consistency. Revisit only if a measured need (for example semantic search) appears.
