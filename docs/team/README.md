# Team onboarding

The full onboarding doc (context, decisions, architecture diagram, workstreams) is the shared Claude doc **"WhereWeGo — Team onboarding"**; ask Chadha for access. This file is the in-repo summary.

## Read in this order (20 minutes)
1. `README.md`: what the product is and how to run it
2. `docs/architecture.md`: target architecture on AWS, and §9 for what is built today
3. `docs/adr/README.md`: the 12 decisions
4. `docs/data-contracts.md`: the contracts the frontend and backend share
5. `CLAUDE.md` + `AGENTS.md`: the rules every person and agent follows

## Workstreams

| Workstream | Session | Folders | Issues |
|---|---|---|---|
| Backend core | Agent A, branches `be/` | `src/moment_intelligence/**`, `apps/api/**`, backend `tests/`, `migrations/` | label `ws:backend` (#4 Alembic, #5 provider adapters, #6 Intent Agent, #7 admin auth) |
| Frontend and demo | Agent B, branches `fe/` | `wherewego-web` repo, `docs/local-fullstack-demo.md` | label `ws:frontend` (#8 Playwright e2e, #9 demo polish), blocked by #3 |
| Data and evaluation | Agent C, branches `data/` | `evaluation/**`, `data_platform/**`, `docs/evaluation.md` | label `ws:data` (#10 dataset, #11 ranking eval, #12 local medallion pipeline) |
| Product, pitch, merges | Chadha | issues, merges, Lovable prompts, keys | label `owner:chadha` (#3 Lovable → GitHub sync) |

Suggested order: #10 before #11 (the harness needs the dataset); #6 coordinates its format with #10; #8 starts once #3 is done.

## How we work
- Every task is an issue; every change is a small PR with `Closes #n`; a different person or agent reviews; Chadha merges.
- Shared files (`contracts.py`, `pyproject.toml`, `AGENTS.md`, `CLAUDE.md`, `docs/architecture.md`, ADRs) only change in a `contract-change` PR.
- Lovable writes to `main` of `wherewego-web`; Claude Code works there only on branches and pulls before starting.
- Handoff on the issue when you stop: done / next / blocked.

## Starting a Claude Code session
Use the matching prompt in [agent-kickoff.md](agent-kickoff.md).
