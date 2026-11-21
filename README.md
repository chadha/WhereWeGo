# WhereWeGo

**Product brand:** Create Your Memories
**Technical platform:** Moment Intelligence
**Core promise:** "Because the moments you share are what last."

An AI experience discovery platform for Berlin. It helps people find memorable experiences with a partner, family, friends or on their own, and turns them into personalized *Moment Collections* that link to approved provider booking pages.

It is not a generic event directory and not a generic chatbot. The website does not process bookings or payments.

## Status

Architecture, decisions and a local discovery backend (FastAPI + Tavily adapter, see below). **No cloud infrastructure has been deployed.** Everything that can incur cost is disabled by default and gated behind explicit human approval (see [`infra/approval-gates.md`](infra/approval-gates.md)).

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
| [docs/adr/](docs/adr) | Architecture Decision Records ADR-001 to ADR-012 |
| [docs/security-and-privacy.md](docs/security-and-privacy.md) | Security architecture, threat model, GDPR data minimization |
| [docs/evaluation.md](docs/evaluation.md) | How we prove the AI is reliable: intent, ranking, operations, business metrics |
| [docs/growth-and-ai-discoverability.md](docs/growth-and-ai-discoverability.md) | SEO / AEO / GEO content structure and AI crawler readiness |
| [docs/roadmap.md](docs/roadmap.md) | Phases, acceptance gates and Sprint 1 checklist |
| [infra/](infra) | AWS IaC layout (Terraform, plan-only), cost estimates, approval gates, resource inventory |
| [AGENTS.md](AGENTS.md) | Master brief for coding agents (Codex, Claude Code) working in this repo |

## Local full-stack demo

Backend + Lovable frontend on your laptop, with a 2-minute demo script: see [docs/local-fullstack-demo.md](docs/local-fullstack-demo.md). Quick start: `./scripts/run_local.sh` (SQLite) or `docker compose up --build` (PostgreSQL).

## Run the backend locally

The first vertical slice is a FastAPI service with `POST /v1/discover`, backed by Tavily web search through a dedicated provider adapter. Without a Tavily key it uses a clearly labelled demo catalogue. It needs no AWS resources.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Optional: live web search through Tavily (1 basic-search credit per discovery)
export TAVILY_API_KEY=tvly-...        # never commit it; see .env.example

uvicorn app.main:app --app-dir apps/api --reload
```

Try it:

```bash
curl -s localhost:8000/v1/health/ready
curl -s -X POST localhost:8000/v1/discover \
  -H 'content-type: application/json' \
  -d @contracts/examples/discovery_request.json
```

Interactive API docs: http://localhost:8000/docs

| Endpoint | Purpose |
|---|---|
| `POST /v1/discover` | Validated `DiscoveryRequest` → `MomentCollectionResponse` |
| `GET /v1/collections/{id}` | Fetch a generated collection |
| `GET /v1/offers/{offer_id}?collection_id=` | Offer details |
| `POST /v1/events` | Client events: `offer_viewed`, `offer_clicked`, `collection_viewed` |
| `GET /v1/offers/{offer_id}/go?collection_id=&session_id=` | Records `offer_clicked` and redirects to the stored source URL only |
| `GET /v1/health/live`, `/v1/health/ready` | Health (reports provider mode, never secrets) |
| `GET /v1/demo/summary` | Aggregate demo numbers (disable with `DEMO_SUMMARY_ENABLED=false`) |

Checks (the same ones CI runs, with no deploy step):

```bash
ruff check . && ruff format --check . && mypy && pytest -q
python scripts/export_schemas.py   # regenerate contracts/schemas/*.json and openapi.json
```

What the slice guarantees: at most five `basic` Tavily results per discovery; results deduplicated; source URL, title, search timestamp and query kept as provenance; price and availability always `unknown` for web results (never parsed from page text); no affiliate or booking URLs invented; unsafe URLs dropped; bounded retries, timeouts, a circuit breaker and an honest fallback when search fails; consent-aware, idempotent events. See [docs/architecture.md §9](docs/architecture.md#9-current-implementation-local-vertical-slice).

## Planned stack

Python 3.12+ (verify library compatibility at scaffold time), FastAPI, Pydantic, SQLAlchemy + Alembic, PostgreSQL, pytest, Ruff, mypy, OpenTelemetry, Amazon Bedrock behind a provider-neutral model gateway, Amazon SQS, Amazon S3, Databricks on AWS (Unity Catalog, Delta, MLflow), Terraform.

Versions are not pinned by guesswork: check package compatibility when scaffolding.
