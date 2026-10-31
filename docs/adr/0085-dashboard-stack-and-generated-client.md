# ADR-0085: Dashboard stack: Next.js static export, openapi-typescript client, Vitest
Status: Accepted under the autonomous mandate · Date: 2026-10-24 (WS-12)

## Context
CLAUDE.md names Next.js + React Flow for apps/web; .claude/rules/frontend.md requires
TypeScript strict, an API client generated from the FastAPI OpenAPI schema and no
business logic in the frontend; ADR-0029 deploys the dashboard as a static export served
by Caddy next to the API. Nothing had fixed the exact toolchain, how the client is
generated, or how the generated client is kept in step with the backend.

## Decision
- **Next.js 16.4.3 (App Router) with `output: "export"` and `trailingSlash: true`**,
  React 19.3.1, TypeScript 5.9.3 in strict mode with `noUncheckedIndexedAccess`.
  Every dependency is pinned to an exact version in apps/web/package.json; the
  lockfile is committed and `npm ci` is the only install path in CI.
- **Client generation**: `openapi-typescript` 7.13.0 turns the committed snapshot
  `apps/web/openapi.json` into `src/api/schema.d.ts` (`npm run gen:api`, flags
  `--alphabetize --export-type`). A hand-written wrapper of about a hundred lines,
  `src/api/client.ts`, sends the bearer token, encodes query strings, maps non-2xx to
  `ApiError`, and exposes one method per endpoint typed by aliases in `src/api/types.ts`
  that all point at `components["schemas"]`. No request or response shape is written by
  hand.
- **Snapshot discipline**: `openapi.json` is produced offline from the test harness
  (`Harness.build().app.openapi()`), never from a running server. A Python test (to be
  added by the coordinator in tests/api, described in the WS-12 handover) diffs the live
  schema against the snapshot, so a backend change that alters the contract fails the
  suite until `openapi.json` and the generated types are regenerated.
- **Tests**: Vitest 4.1.12 with jsdom and Testing Library; esbuild's automatic JSX
  runtime, no Vite React plugin. Every page has tests for loading, empty, error and
  data states against a fake `RippleApi`.
- **Lint and format**: ESLint 9 flat config from `eslint-config-next` (core-web-vitals
  + typescript) with jsx-a11y's strict rules layered on, Prettier 3.9; `npm run lint`
  runs ESLint, Prettier's check and `tsc --noEmit`.
- **Styling**: one global stylesheet with CSS custom properties and a dark scheme via
  `prefers-color-scheme`; no CSS framework, no component library, no analytics or
  third-party scripts.

## Alternatives considered
- `openapi-fetch` (same authors) for the wrapper: typed per path, but one more runtime
  dependency for what is forty lines of fetch. The wrapper here is smaller and the
  types still come from the generator. Lost on dependency count.
- A hand-written client with hand-written types: the only way it stays correct is
  discipline, which is what the rule forbids relying on. Lost.
- Orval or openapi-generator (full client generation): produce large clients with
  their own fetch layer and templates to maintain. Lost on size.
- Jest + SWC: more configuration for the same Testing Library tests; Vitest reads the
  tsconfig paths directly. Lost.
- Tailwind or a UI kit: adds build steps and a dependency tree to a six-page tool whose
  styling requirement is "colour and a label". Lost.
- Next.js server runtime instead of a static export: would need a Node process on the
  VPS and a second thing to deploy; the dashboard has no server-side work. Lost;
  ADR-0029 already assumed the export.

## Consequences
- The route per memory cannot be pre-rendered, so the detail page reads the id from a
  query string (ADR-0086).
- `next build` rewrites `tsconfig.json` (`jsx: react-jsx`, extra `include`); the file
  is excluded from Prettier so lint stays green after a build.
- Node 22.19 is below the engine range jsdom 30 declares (a warning, tests pass);
  upgrading Node removes the warning.
- npm 10.9 hit an internal resolver error on this dependency set; `.npmrc` sets
  `legacy-peer-deps=true`, which makes `npm ci` deterministic on the committed lockfile.

## Revisit if
The backend grows a websocket or streaming surface the generator cannot describe, or
the dashboard needs server-side rendering for sharing links.
