# ADR-006: Queue-based asynchronous event ingestion

**Status:** Accepted
**Date:** 2026-11-21

## Context
Analytics must never slow down or break the discovery request path.

## Decision
The API publishes validated, idempotent events to Amazon SQS and returns immediately. A consumer writes them to the S3 raw zone for Databricks.

## Consequences
Decoupled, resilient ingestion. Requires dead-letter handling, idempotency and monitoring of queue age.
