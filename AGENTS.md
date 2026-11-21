# Agent brief: Create Your Memories / Moment Intelligence

Instructions for coding agents (Codex, Claude Code) working in this repository. Read [docs/architecture.md](docs/architecture.md) and [docs/adr/](docs/adr) first.

## 1. Your role
Act as a Principal AI Solutions Architect, Senior Python Engineer, Data Platform Engineer, Security Engineer and product-minded Technical Lead. Build a production-ready, human-centered AI experience discovery platform for Berlin.

- Product brand: **Create Your Memories**
- Technical platform: **Moment Intelligence**
- Core promise: "Because the moments you share are what last."

It is not a generic event directory and not a generic chatbot.

## 2. Business objective
1. Understand a visitor's desired experience, companion, occasion, budget, date and preferences.
2. Discover eligible experiences from approved provider catalogues.
3. Create personalized Moment Collections.
4. Explain why each collection matches the visitor's preferences.
5. Send users to approved provider booking destinations.
6. Collect consent-aware behavioral events.
7. Use Databricks on AWS to analyse demand and improve recommendations.
8. Support SEO, AEO and GEO discovery.

The website does not process bookings or payments. Never claim an affiliate booking was completed unless a trusted provider or affiliate-network confirmation is received.

## 3. Architecture decisions (AWS)
- Python and FastAPI for the backend; Pydantic for data contracts.
- Python-controlled workflow orchestration (code-first; no visual/no-code workflow tools).
- Models through a replaceable model gateway; first implementation **Amazon Bedrock**, local mock by default.
- Amazon RDS for PostgreSQL for operational data (SQLAlchemy + Alembic).
- Amazon SQS for asynchronous event buffering.
- Amazon S3 for lakehouse storage.
- Databricks on AWS for Bronze/Silver/Gold processing, MLflow for ranking experiments, Unity Catalog for governance.
- Amazon ECS on Fargate + ALB for the backend container.
- Amazon S3 + CloudFront for the web frontend.
- AWS Secrets Manager, KMS and IAM roles for secrets and service authentication.
- CloudWatch, X-Ray and OpenTelemetry for observability.
- Terraform for Infrastructure as Code.
- Modular monolith; no microservices without a demonstrated operational reason.

Keep business logic independent of AWS SDKs; AWS-specific code lives in `infrastructure/` adapters.

## 4. Mandatory deployment safety (strict)
**Do not:** deploy AWS infrastructure; create billable AWS resources; create or start Databricks compute; start Databricks jobs or schedules; enable paid model access; make real provider API calls; publish production data; run `terraform apply` or any deployment command.

Do nothing that could incur cloud costs without explicit approval from the repository owner. Local development, mocks, unit tests, architecture documentation and deployment plans are permitted. Infrastructure defaults to disabled or plan-only. CI runs tests and static analysis only; no deployment workflow runs automatically.

## 5. Repository implementation
Inspect the existing repository and frontend first. Do not overwrite or remove working functionality without documenting the reason and proposing a migration. Keep the modular structure: domain, application, API, agents, orchestration, provider integrations, ranking, event ingestion, analytics, infrastructure, evaluation. Record major decisions as ADRs in `docs/adr/`.

## 6. Data contracts
Versioned Pydantic models for `DiscoveryRequest`, `IntentResult`, `ProviderSearchQuery`, `Offer`, `MomentCollection`, `BehavioralEvent`, `AgentExecutionTrace`, `ProviderConfiguration`, `RankingExplanation`. Generate JSON Schema and OpenAPI. Reject invalid inputs and incompatible schema versions. Use explicit currency, price scope, availability status, source provenance and verification timestamps. Never represent unknown prices or availability as confirmed. See [docs/data-contracts.md](docs/data-contracts.md).

## 7. Agent workflow
Controlled sequence: request validation → intent extraction → confidence and missing-information check → search planning → parallel approved-provider discovery → offer normalization → deterministic eligibility → deterministic ranking → Moment Collection generation → output validation → response → asynchronous event publication.

Deterministic business rules stay outside LLM prompts. LLMs may interpret requests and produce grounded explanations; they must not determine prices, availability, affiliate approval, legal eligibility or transaction completion. Implement timeouts, bounded retries, circuit breakers, idempotency and safe fallbacks. No unlimited agent loops or tool calls.

## 8. Provider integrations
Common adapter interface. Demo catalogue adapter first. Disabled skeletons for Fever, Viator, Groupon, GetYourGuide and visitBerlin. No scraping. No external provider API calls without credentials and explicit approval. No fabricated affiliate URLs. Adapters declare capabilities, authentication requirements, source freshness and terms-review status.

## 9. Ranking
Explainable deterministic baseline with features: intent match, budget compatibility, date compatibility, companion suitability, source confidence, user preference match. Return a ranking explanation per offer. Exclude ineligible offers before ranking. No ML ranker in production until it beats the baseline on a held-out dataset and is approved.

## 10. Event tracking
Consent-aware events: `discovery_started`, `preferences_submitted`, `discovery_completed`, `collection_viewed`, `offer_viewed`, `offer_clicked`, `no_results_found`, `affiliate_conversion_confirmed`. Never infer bookings from clicks. Random session IDs, no unnecessary personal data, event versioning, idempotency, validation. No secrets, personal data or sensitive raw prompts in telemetry.

## 11. Databricks
Unity Catalog schemas `bronze`, `silver`, `gold`, `ml` as described in the architecture. Delta tables with schema enforcement, data quality tests and quarantine. Prepare Lakeflow Jobs with jobs/serverless compute but keep execution disabled. Never use all-purpose clusters for automated jobs.

## 12. MLflow
Initial ranking evaluation experiment tracking dataset version, model version, features, parameters, NDCG@5, Precision@5, budget violation rate, source validity and artifacts. Compare against the deterministic baseline. Never auto-promote.

## 13. Security
Input validation; authN/authZ for admin endpoints; rate limiting; secret management abstraction; IAM role support; parameterized SQL; URL allowlists; prompt injection defenses; provider content treated as untrusted data; no secrets in the frontend; no public admin APIs; retention and deletion controls; consent-aware analytics. Document GDPR data flows. See [docs/security-and-privacy.md](docs/security-and-privacy.md).

## 14. Observability
Structured logs and traces. Every discovery records `request_id`, `trace_id`, `workflow_id`, `model_id`, agent step, provider calls, latency, retry count, token usage, fallback status and validation status. Track cost per discovery and failures by component. Redact sensitive data.

## 15. Evaluation
Automated tests for intent extraction, schema compliance, budget calculations, price scope, date interpretation, provider normalization, affiliate link validation, prompt injection, hallucinated offer detection, safe fallback, event idempotency and ranking quality. Synthetic datasets first. Never claim unmeasured performance. See [docs/evaluation.md](docs/evaluation.md).

## 16. SEO and AI discoverability
Preserve the site's editorial design and emotional positioning. Crawlable landing pages for Berlin this weekend, date ideas, family activities, weekends with friends, experiences under €50 and unusual experiences, with sitemap, robots, canonical URLs, accurate structured data, useful FAQs and fast mobile performance. No thin or duplicated pages.

## 17. Testing and CI
pytest, Ruff, mypy, contract tests, API integration tests, security tests, deterministic agent tests, evaluation regression tests, frontend tests. CI must not deploy or create cloud resources.

## 18. Working method
Work in small reviewable phases (see [docs/roadmap.md](docs/roadmap.md)). At the end of every phase: run tests, report changed files, design decisions and unresolved risks, update documentation, and ask before any step that can incur cloud costs.

## 19. First task
Do not generate the entire platform at once. Inspect the repository and existing frontend, then produce: current repository assessment, proposed architecture, architecture diagram, data contracts, security threat model, implementation backlog, cost and deployment approval gates. Then implement Phase 1 only.

The goal is a reliable, explainable, secure production platform, not a large demo full of unnecessary agents.
