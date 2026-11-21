# ADR-003: Amazon Bedrock models behind a provider-neutral gateway

**Status:** Accepted
**Date:** 2026-11-21

## Context
The original design used Microsoft Foundry. With the move to AWS we need managed model access, but we must not lock business logic to one provider or model.

## Decision
All model calls go through an internal `ModelGateway` interface. The first production implementation uses Amazon Bedrock. A local mock implementation is the default for development and tests. Model IDs are configuration, per workflow step.

## Consequences
Models can be swapped or compared (cost, latency, quality) without touching business logic. Every call records model ID, latency, tokens and cost.
