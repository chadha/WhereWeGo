# Evaluation: how we prove the AI is reliable

We do not measure success by the agent answering beautifully. Evaluation has four layers. All targets below are **proposed acceptance criteria, not achieved results.** Never claim performance that has not been measured.

## A. Intent evaluation
A test dataset of roughly 100–200 human-labeled requests.

| Metric | What it measures | Initial target |
|---|---|---|
| Schema validity | Correct JSON contract | ≥ 99% |
| Companion accuracy | Correct companion extraction | ≥ 95% |
| Budget extraction | Correct budget and currency | ≥ 98% |
| Date extraction | Correct date interpretation | ≥ 95% |
| Unsupported inference | Invented preferences | 0 critical cases |

## B. Discovery and ranking evaluation

| Metric | Question |
|---|---|
| Precision@5 | Are the top 5 offers actually suitable? |
| NDCG@5 | Is the ordering sensible? |
| Budget violation rate | Did we suggest experiences over budget? |
| Invalid offer rate | Did an invalid offer appear? |
| Stale source rate | Did we use outdated information? |
| No-result rate | How many requests found nothing? |

**Critical acceptance criteria:** zero invented prices; zero fabricated booking confirmations; zero unapproved affiliate destinations; zero known budget violations; every displayed offer has provenance.

## C. Agent reliability and operations

| Metric | Measurement |
|---|---|
| API p95 latency | User experience |
| Model latency | Bedrock performance |
| Tool failure rate | Provider reliability |
| Workflow completion rate | Orchestration reliability |
| Fallback rate | Resilience |
| Tokens per discovery | AI cost |
| Cost per qualified discovery | Unit economics |

Initial production design targets:
- API p95 below 3 seconds for cached or deterministic paths.
- AI-assisted discovery p95 below 8 seconds, subject to model and provider latency.
- 99.5% monthly availability initially; a more ambitious SLO only with real operating evidence.
- Every failure traceable through a request/trace ID.

These numbers are not considered verified until load testing confirms them.

## D. Business evaluation
Measure: discovery completion rate, collection view rate, offer click-through rate, qualified intent cost, confirmed affiliate conversion rate (if reporting is available), revenue per completed eligible booking, demand by segment, unmet demand.

**North Star Metric: Qualified Moment Discoveries**: a completed discovery session containing a suitable collection, with one or more offers that have a clear source and an understandable price/eligibility status. This beats raw website visits or chatbot message counts.

## Automated tests to build
Intent extraction, schema compliance, budget calculations, price scope, date interpretation, provider normalization, affiliate link validation, prompt injection, hallucinated offer detection, safe fallback behavior, event idempotency, ranking quality. Use synthetic datasets first and document baseline results and limitations.

## MLflow
Create an initial ranking evaluation experiment tracking dataset version, model version, feature definitions, parameters, NDCG@5, Precision@5, budget violation rate, source validity and artifacts. Compare every candidate against the deterministic baseline. Never auto-promote a model to production.
