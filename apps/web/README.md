# Ripple dashboard (apps/web)

Home, the write flows (say what changed, add an opening, resume review, Telegram link),
the belief inspector, questions, map, recommendations and account (FR-1, FR-2, FR-4,
FR-7, FR-12, FR-13, FR-15). Next.js static export, TypeScript strict, client generated
from the API's OpenAPI schema. Decisions: docs/adr/0085, 0086, 0087, 0130, 0131. How it
works: docs/learning/dashboard.md.

The quickest way to see it with a real API: from the repository root,
`uv run python -m tools.local_run --seed-demo` (docs/learning/local-run.md).

## Commands (run inside apps/web)

| Command           | What                                                                                                                                                          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `npm ci`          | install exactly what the lockfile says                                                                                                                        |
| `npm run dev`     | dev server on :3000 (set `NEXT_PUBLIC_RIPPLE_API_BASE=http://localhost:8000` to hit a bare uvicorn, started with `RIPPLE_CORS_ORIGINS=http://localhost:3000`) |
| `npm run lint`    | ESLint, Prettier check, `tsc --noEmit`                                                                                                                        |
| `npm test`        | Vitest component tests (offline, fake API)                                                                                                                    |
| `npm run build`   | static export into `out/`                                                                                                                                     |
| `npm run gen:api` | regenerate `src/api/schema.d.ts` from `openapi.json`                                                                                                          |

## Developing against a local API

`next dev` serves on :3000 and the API runs on :8000, so the browser calls a second
origin. Start the API with `RIPPLE_CORS_ORIGINS=http://localhost:3000` (comma-separated
for several origins; development only, production is same-origin through Caddy) and the
dashboard with `NEXT_PUBLIC_RIPPLE_API_BASE=http://localhost:8000 npm run dev`.

## Regenerating the API client

1. From the repository root:
   `uv run python -c "from tests.api.harness import Harness; import json; print(json.dumps(Harness.build().app.openapi(), indent=2, sort_keys=True))" > apps/web/openapi.json`
2. `cd apps/web && npm run gen:api && npm run lint`
   A Python test diffs `openapi.json` against the live schema so the two cannot drift
   silently.

## Deploy

`npm run build`, copy `out/` to `infra/web-dist`; Caddy serves it at the site root and
proxies `/api/*` to the API (infra/Caddyfile, ADR-0029).

## Rules

- No business logic here: the pages render what the API returns. `tests/no-business-logic.test.ts` scans `src/` for rule-shaped code.
- Memory states show colour AND text. RETIRED never appears in a list (I1).
- The token lives in sessionStorage only. No analytics, no third-party scripts.
- Visual values are tokens in `src/app/globals.css` (light and dark); no remote fonts,
  no CDN (the CSP allows none).
