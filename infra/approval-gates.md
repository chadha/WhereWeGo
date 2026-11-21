# Approval gates

Every infrastructure change goes through these steps, in order:

1. **`terraform plan`** for the target environment, attached to the pull request.
2. **Cost estimate and resource inventory**: update `cost-estimates.md` and `resource-inventory.yaml` (for example with Infracost or the AWS Pricing Calculator).
3. **Security review**: IAM policies, network exposure, encryption, secrets.
4. **Explicit human approval** naming the exact resources and the expected monthly spend.
5. **Deployment by an authorized person.** Never by CI or an AI agent.

## Before anything billable
- AWS Budgets alerts and Cost Anomaly Detection exist for the account/environment.
- Every resource is tagged with `project`, `env` and `cost_owner`.
- Databricks: budget policy set, jobs use jobs/serverless compute, schedules start disabled.
- Bedrock: per-environment usage alarms; token budget per discovery enforced in code.

## Never without approval
Creating billable AWS resources, starting Databricks compute or jobs, enabling paid model access in production, calling real provider APIs, publishing production data, running `terraform apply`.
