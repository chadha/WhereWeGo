# Roadmap and acceptance gates

Do not give a coding agent one prompt that says "build the whole platform". Every phase ends with evidence.

## Build and release gates

| # | Gate | Scope | Acceptance |
|---|---|---|---|
| 1 | Foundation (local only) | Architecture decisions, repository assessment, contracts, threat model, local dev environment | Contracts validate, tests pass |
| 2 | Working discovery product | FastAPI + demo provider catalogue + ranking + Moment Collections + frontend integration | End-to-end discovery works without cloud services |
| 3 | Agent intelligence | Model gateway (Bedrock + local mock), Intent Agent, Curator, controlled Python workflow, fallback logic | Evaluation dataset passes agreed thresholds; mock mode still works |
| 4 | Data intelligence | Event contracts, local event fixtures, Bronze/Silver/Gold pipeline, MLflow experiment | Repeatable pipeline, data quality tests, baseline ranking evaluation |
| 5 | Production readiness | Security, observability, load tests, disaster recovery assumptions, Terraform review, cost estimate | Production-readiness checklist signed off |
| 6 | Cloud activation (**requires approval**) | AWS and Databricks provisioning, Bedrock model access, provider credentials, production data | Explicit approval for the exact resources and expected spend before execution |

## Implementation phases
0. Inspect the repository and write architecture decisions.
1. Domain models and data contracts.
2. FastAPI backend and PostgreSQL data layer.
3. Deterministic demo catalogue and ranking.
4. Python orchestration and model gateway (Bedrock) with local mock mode.
5. Frontend integration.
6. Event collection and asynchronous buffering (SQS).
7. Databricks Bronze/Silver/Gold pipelines.
8. MLflow evaluation.
9. Security, observability and load testing.
10. AWS infrastructure and deployment documentation, **without deploying**.

At the end of every phase: run tests, report changed files, report design decisions, report unresolved risks, update documentation, and ask before any step that can incur cloud costs.

## Sprint 1 checklist (0/9)
We start with the engineering foundation, not with creating AWS resources.

- [ ] Inspect the existing Lovable/GitHub frontend and repository
- [x] Create architecture.md and ADR-001 to ADR-011 *(this commit)*
- [ ] Define Pydantic contracts and JSON Schemas
- [ ] Create FastAPI skeleton and health endpoints
- [ ] Implement demo provider adapter and normalized Offer model
- [ ] Implement deterministic eligibility and ranking
- [ ] Create synthetic discovery evaluation dataset
- [ ] Create local event schema and event publisher mock
- [ ] Write security threat model and cloud cost approval gates *(first draft in this commit)*

## What makes this a strong Senior AI Architect project
Not the number of agents or cloud services. Evidence of five capabilities:
1. **Architecture:** clear separation between product, AI orchestration, data platform and infrastructure.
2. **Reliability:** agents with contracts, bounded execution, fallbacks and evaluation.
3. **Governance:** Unity Catalog, data lineage, permissions, privacy and model approval.
4. **Business intelligence:** Databricks discovers unmet demand and turns it into product and growth decisions.
5. **Operational economics:** measurable cost of discovery, tokens, model calls, provider calls and data jobs.

Possible case study title: *Designing a Production-Ready Agentic Experience Discovery Platform on AWS and Databricks.*
