# ADR-007: Databricks medallion lakehouse

**Status:** Accepted
**Date:** 2026-11-21

## Context
We want to learn from demand (unmet demand, budgets, funnels, channels) and later improve ranking, with governance and lineage.

## Decision
Use Databricks on AWS with Unity Catalog and Delta tables in a Bronze/Silver/Gold/ML layout, with data quality tests and a quarantine zone. Jobs use jobs/serverless compute, never all-purpose clusters. Schedules are disabled by default.

## Consequences
Strong governance and analytics. Costs are real even with serverless, so execution stays behind approval gates.
