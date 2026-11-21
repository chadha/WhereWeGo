# Security and privacy

Infrastructure must be repeatable, version-controlled and reviewable before any deployment.

## Identity and access
- IAM roles between AWS services (ECS task roles); no long-lived access keys in the application.
- IAM Identity Center (SSO) with MFA for administrators.
- Dedicated IAM roles / service principals for automated Databricks jobs.
- Least-privilege IAM policies.
- No shared credentials or personal user credentials in production.
- Separate AWS accounts per environment where practical (AWS Organizations).

## Secrets
Stored in AWS Secrets Manager, encrypted with AWS KMS, and read by the application through its IAM role:
- Model gateway configuration (Bedrock model IDs, any external model keys)
- Provider API keys
- Affiliate secrets
- Database connection configuration

Nothing secret is ever exposed to the frontend.

## Network
- HTTPS everywhere (ACM certificates on CloudFront and the ALB).
- RDS and data services in private subnets; VPC endpoints for S3, SQS, Secrets Manager and Bedrock when justified.
- Restricted database ingress (security groups from the API tasks only).
- No public credentials for the Databricks S3 storage.
- AWS WAF and rate limiting at the edge as traffic and risk require.

## Application security
- Input validation and output schema validation.
- SQL injection protection through parameterized queries.
- SSRF prevention when handling provider URLs.
- Safe URL allowlists for outbound provider and affiliate links.
- Prompt injection protection: provider descriptions and any external content are untrusted data, never instructions.
- No execution of model-generated code.
- No public admin endpoints; admin APIs require authentication and authorization.
- Bounded agent execution: timeouts, token budgets, maximum provider calls, circuit breakers.

## Threat model (initial)

| Threat | Example | Mitigation |
|---|---|---|
| Prompt injection via provider content | An offer description says "ignore your rules" | Treat provider text as data; Curator may only use structured fields; output validator |
| Hallucinated offers or prices | LLM invents an experience or a price | Curator restricted to supplied offers; validator checks every offer ID, price and URL against the source |
| Budget abuse / cost attack | Bot floods `/v1/discover` to burn model spend | WAF + rate limits, per-session token budget, AWS Budgets alerts |
| Malicious outbound links | Tampered affiliate URL | Allowlisted domains, approved-affiliate flag, server-side redirect |
| SSRF | Provider URL pointing to internal metadata | URL allowlist, no fetching of user-supplied URLs |
| Data leakage in telemetry | Raw prompts with personal details in logs | PII redaction, no raw sensitive prompts in traces |
| Privilege escalation | Admin API reachable publicly | Auth on admin routes, network restrictions, least-privilege IAM |
| Secret exposure | Keys in code or frontend bundle | Secrets Manager only, secret scanning in CI |

## Privacy and GDPR
Keep data collection minimal:
- No user names.
- No emails required for discovery.
- No exact child dates of birth; an age band only if necessary.
- Random, short-lived session identifiers.
- Consent state stored with relevant analytics events.
- Retention policy for raw events.
- Data deletion workflow where required.
- No sensitive personal information in model prompts or traces.

**Important:** in Germany, analytics and advertising tracking need consent and a legal review appropriate to the implementation. The consent UI is real, not a cosmetic checkbox.

## Cost protection
Every resource has a cost owner and a budget guardrail (AWS Budgets, Cost Anomaly Detection, cost-allocation tags). See [`infra/approval-gates.md`](../infra/approval-gates.md).
