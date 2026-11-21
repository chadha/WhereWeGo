# ADR-010: No deployment without explicit approval

**Status:** Accepted
**Date:** 2026-11-21

## Context
Cloud and data platform resources cost money, and automated agents must never create spend on their own.

## Decision
Everything that can incur cost is off by default: infrastructure deployment, Databricks compute and schedules, paid model calls (local mock by default), provider API calls, production data ingestion. CI runs tests and static analysis only. Every infrastructure change goes through `terraform plan`, a cost estimate and resource inventory, a security review, explicit human approval, and deployment by an authorized person. `terraform apply` is never automated.

## Consequences
Slower first deployment, predictable spend, and a clear audit trail.
