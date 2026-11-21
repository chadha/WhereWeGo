# CLAUDE.md

@AGENTS.md

## Team mode (read this before doing anything)

Several people and three Claude Code sessions work in this repo at the same time. Stay in your lane.

1. **Find your workstream** in `docs/team/README.md` and work only in its folders:
   - Agent A, backend core (`ws:backend`): `src/moment_intelligence/**`, `apps/api/**`, backend `tests/`, `migrations/`
   - Agent B, frontend and demo (`ws:frontend`): the `wherewego-web` repo, `docs/local-fullstack-demo.md`
   - Agent C, data and evaluation (`ws:data`): `evaluation/**`, `data_platform/**`, `docs/evaluation.md`
2. **Work from a GitHub issue.** Comment "starting" on it first. If no issue fits, open one before coding.
3. **Branch:** `be/<issue>-<slug>`, `fe/<issue>-<slug>` or `data/<issue>-<slug>`. Never push to `main`. Never merge your own PR.
4. **Shared files** need a PR labelled `contract-change` and a note on the affected issues: `src/moment_intelligence/domain/contracts.py`, `pyproject.toml`, `AGENTS.md`, `CLAUDE.md`, `docs/architecture.md`, `docs/adr/*`. After contract changes run `python scripts/export_schemas.py`.
5. **Before opening a PR** run and paste the real output: `ruff check . && ruff format --check . && mypy && pytest -q`.
6. **When you stop,** comment on the issue: done / next / blocked.

## Commands
- Install: `pip install -e ".[dev]"`
- Run API: `./scripts/run_local.sh` (SQLite) or `uvicorn app.main:app --app-dir apps/api`
- Tests: `pytest -q` (Tavily is always mocked in tests)
- Schemas: `python scripts/export_schemas.py`

## Never
Deploy or create cloud resources, call real provider APIs without approval, put secrets in code or logs, invent prices/availability/booking links, or claim results you did not measure. GitHub on this repo: use the REST API (`gh api repos/chadha/wherewego/...`); GraphQL is not available from some sessions.
