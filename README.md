# WhereWeGo

**Product brand:** Create Your Memories
**Technical platform:** Moment Intelligence
**Core promise:** "Because the moments you share are what last."

An AI experience discovery platform for Berlin. It helps people find memorable experiences with a partner, family, friends or on their own, and turns them into personalized *Moment Collections* that link to approved provider booking pages.

It is not a generic event directory and not a generic chatbot. The website does not process bookings or payments.

## Status

Architecture and decisions only. **No cloud infrastructure has been deployed.** Everything that can incur cost is disabled by default and gated behind explicit human approval (see [`infra/approval-gates.md`](infra/approval-gates.md)).

## Key decision

> **Production-ready architecture from day one, but gradual, controlled deployment.**
> Production-grade thinking, code, contracts, tests, security, observability and CI from the first commit. Paid cloud resources run only when there is a clear need and approved cost.

- **Cloud:** AWS. This is the only change from the original Azure design; see [ADR-011](docs/adr/ADR-011-aws-as-cloud-platform.md).
- **Orchestration:** Python-controlled workflow, not a free-running multi-agent swarm.
- **AI's role:** LLMs interpret requests and write grounded explanations. Prices, budgets, eligibility, ranking and affiliate links stay deterministic and testable.
- **Shape:** modular monolith first, no early microservices.

## Documentation map

| Document | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Target architecture on AWS, diagrams, layers, service choices, agent workflow, data platform |
| [docs/data-contracts.md](docs/data-contracts.md) | Versioned contracts: DiscoveryRequest, IntentResult, Offer, BehavioralEvent, MomentCollectionResponse |
| [contracts/examples/](contracts/examples) | JSON examples of every contract |
| [docs/adr/](docs/adr) | Architecture Decision Records ADR-001 to ADR-011 |
| [docs/security-and-privacy.md](docs/security-and-privacy.md) | Security architecture, threat model, GDPR data minimization |
| [docs/evaluation.md](docs/evaluation.md) | How we prove the AI is reliable: intent, ranking, operations, business metrics |
| [docs/growth-and-ai-discoverability.md](docs/growth-and-ai-discoverability.md) | SEO / AEO / GEO content structure and AI crawler readiness |
| [docs/roadmap.md](docs/roadmap.md) | Phases, acceptance gates and Sprint 1 checklist |
| [infra/](infra) | AWS IaC layout (Terraform, plan-only), cost estimates, approval gates, resource inventory |
| [AGENTS.md](AGENTS.md) | Master brief for coding agents (Codex, Claude Code) working in this repo |

## Planned stack

Python 3.12+ (verify library compatibility at scaffold time), FastAPI, Pydantic, SQLAlchemy + Alembic, PostgreSQL, pytest, Ruff, mypy, OpenTelemetry, Amazon Bedrock behind a provider-neutral model gateway, Amazon SQS, Amazon S3, Databricks on AWS (Unity Catalog, Delta, MLflow), Terraform.

Versions are not pinned by guesswork: check package compatibility when scaffolding.
