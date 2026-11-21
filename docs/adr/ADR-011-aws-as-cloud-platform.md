# ADR-011: AWS as the cloud platform

**Status:** Accepted
**Date:** 2026-11-21

## Context
The original architecture targeted Azure (Static Web Apps, Container Apps, Microsoft Foundry, Azure Databricks, Key Vault, Application Insights). The team decided to use AWS instead. Nothing else in the design changes.

## Decision
Map each capability to AWS: S3 + CloudFront (frontend), ECS on Fargate + ALB (API), Amazon Bedrock behind the model gateway (models), RDS for PostgreSQL (operational DB), SQS (events), S3 (lake), Databricks on AWS (lakehouse, Unity Catalog, MLflow), Secrets Manager + KMS (secrets), IAM roles and IAM Identity Center (identity), CloudWatch + X-Ray via OpenTelemetry (observability), AWS WAF (edge), AWS Budgets + Cost Anomaly Detection (cost), Terraform (IaC). Keep business logic free of AWS SDK calls so it stays portable.

## Consequences
One cloud and IAM model for the whole platform. Databricks, PostgreSQL, OpenTelemetry and the gateway pattern keep the core portable. All contracts, rules, gates and evaluation targets are unchanged.
