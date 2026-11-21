# Infrastructure (AWS, Terraform)

**Plan-only.** Nothing in this folder may be applied automatically.

```
infra/
├── aws/
│   ├── modules/            # reusable Terraform modules (network, api, db, queue, lake, ...)
│   └── environments/
│       ├── dev/
│       ├── staging/
│       └── prod/
├── resource-inventory.yaml # every planned resource, owner and phase
├── cost-estimates.md       # assumptions and monthly estimates per environment
└── approval-gates.md       # the human approval process
```

## Rules
- CI runs `terraform fmt -check`, `terraform validate` and `terraform plan` only. There is **no deploy job**.
- `terraform apply` is never run by CI, Codex, Claude Code or any automated workflow.
- Remote state (S3 + locking) is itself a resource and needs approval before creation.
- Every change follows [approval-gates.md](approval-gates.md).

## Deployment safety policy (default: OFF)
- Infrastructure deployment: disabled.
- Databricks job schedules: disabled.
- Databricks compute: no automatic start.
- Model calls: local mock by default.
- Provider API calls: disabled by default.
- Production data ingestion: disabled until approved.
- CI: tests and lint only.
