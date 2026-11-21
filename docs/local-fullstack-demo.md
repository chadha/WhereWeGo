# Local full-stack demo

The demo runs two processes on your laptop:

| Part | Where | Port |
|---|---|---|
| Backend: Moment Intelligence API (FastAPI) | this repo | `8000` |
| Frontend: Lovable app (`/moments` screens) | the Lovable project synced to GitHub | `8080` (Vite) |

Lovable's cloud preview cannot reach `localhost`, so for the local demo the frontend runs locally too. In Lovable: **Settings → GitHub → Connect** and create a repository (for example `wherewego-web`). Lovable keeps it in sync both ways.

## 1. Start the backend

Option A, no Docker (SQLite file, recommended for the pitch):

```bash
cp .env.example .env          # optional: put TAVILY_API_KEY=tvly-... in .env
./scripts/run_local.sh
```

Option B, Docker with PostgreSQL:

```bash
TAVILY_API_KEY=tvly-... docker compose up --build
```

Check it: <http://localhost:8000/v1/health/ready> shows `"live_search": true` with a key, `false` without (demo catalogue).

## 2. Start the frontend

```bash
git clone https://github.com/<you>/wherewego-web && cd wherewego-web
npm install
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev                   # opens http://localhost:8080
```

If the dev server uses another port, add it to `CORS_ORIGINS` in the backend `.env`.

## 3. Demo script (about 2 minutes)
1. Open `http://localhost:8080/moments`. The pill shows "Live web search" (or "Demo catalogue").
2. Pick *Partner*, feelings *surprised* + *connected*, occasion *date*, this weekend, budget €100 total, and switch analytics consent on.
3. "Find our moment" → a titled collection with up to 5 sourced ideas. Point out: source on every card, "Price not verified" instead of invented prices, "Why this?" ranking breakdown.
4. Click "Open source ↗" on one card: the backend records the click and redirects to the real page.
5. Open `/moments/stats`: discoveries, offers shown, views, clicks, CTR. Use these numbers on the slide.

**Plan B (no Wi-Fi):** stop the backend, remove `TAVILY_API_KEY`, restart. The same flow works on the labelled demo catalogue.

## API used by the frontend

| Call | Purpose |
|---|---|
| `GET /v1/health/ready` | Provider mode (`live_search`) |
| `POST /v1/discover` | `DiscoveryRequest` → `MomentCollectionResponse` |
| `POST /v1/events` | `collection_viewed`, `offer_viewed` (fire-and-forget) |
| `GET /v1/offers/{id}/go?collection_id=&session_id=` | Tracked click → 307 to the source page |
| `GET /v1/demo/summary` | Aggregate numbers (set `DEMO_SUMMARY_ENABLED=false` outside demos) |

Full schemas: `contracts/schemas/openapi.json` or <http://localhost:8000/docs>.

### Frontend rules
- No API keys in the frontend; the backend holds `TAVILY_API_KEY`.
- `session_id`: random, kept in `localStorage`; `request_id`: new per search; IDs use only `[A-Za-z0-9_-]`.
- Consent switch is off by default. Without consent, no events are stored.
- If `price.amount` is `null`, show "Price not verified"; show amounts only with the "Illustrative demo" badge when `is_illustrative` is true. Never present availability as confirmed.
- `status: "degraded"` → calm warning + Retry; `status: "no_results"` → empty state.
