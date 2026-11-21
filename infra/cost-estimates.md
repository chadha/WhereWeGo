# Cost estimates

No estimates have been calculated yet. Fill this in during Phase 10 using the AWS Pricing Calculator (or Infracost on the Terraform plan), per environment.

| Resource | Dev | Staging | Prod | Assumptions |
|---|---|---|---|---|
| CloudFront + S3 (web) | TBD | TBD | TBD | Monthly requests, data transfer |
| ECS Fargate + ALB (API) | TBD | TBD | TBD | vCPU/memory per task, task count, hours |
| RDS for PostgreSQL | TBD | TBD | TBD | Instance class, storage, Multi-AZ (prod only) |
| SQS | TBD | TBD | TBD | Events per month |
| S3 data lake | TBD | TBD | TBD | GB stored, requests |
| Databricks on AWS | TBD | TBD | TBD | DBUs per job run, runs per day |
| Amazon Bedrock | TBD | TBD | TBD | Discoveries/month × tokens per discovery × model price |
| CloudWatch / X-Ray | TBD | TBD | TBD | Log GB, traces |
| WAF | TBD | TBD | TBD | Rules, requests |

**Unit economics to track:** cost per qualified discovery = (Bedrock + provider calls + share of infrastructure) ÷ qualified moment discoveries.
