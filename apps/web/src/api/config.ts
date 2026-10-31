/** The API base path. Production serves the dashboard and proxies `/api/*` from one
 * origin (infra/Caddyfile), so the default needs no host. `next dev` can point at a
 * local uvicorn through NEXT_PUBLIC_RIPPLE_API_BASE (inlined at build time). */
export const API_BASE_URL: string = process.env.NEXT_PUBLIC_RIPPLE_API_BASE ?? "/api";
