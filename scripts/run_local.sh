#!/usr/bin/env bash
# Start the Moment Intelligence API locally (no Docker needed).
# Data is kept in ./wherewego-local.db (SQLite). Set TAVILY_API_KEY for live web search.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -e ".[dev]"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export DATABASE_URL="${DATABASE_URL:-sqlite:///./wherewego-local.db}"
if [ -n "${TAVILY_API_KEY:-}" ]; then
  echo "Live web search: Tavily (basic, max 5 results per discovery)"
else
  echo "No TAVILY_API_KEY: using the illustrative demo catalogue"
fi
echo "API docs: http://localhost:8000/docs"
exec uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload
