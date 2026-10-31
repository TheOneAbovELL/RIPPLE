import type { NextConfig } from "next";

// Static export served by Caddy next to the API (ADR-0029, ADR-0086). The App Router
// export carries small inline bootstrap scripts, so the serving CSP needs
// `script-src 'self' 'unsafe-inline'` (nonces are impossible in a static file). Caddy's
// `try_files {path} {path}/ /index.html` needs folder-per-route output, hence
// trailingSlash. Nothing here reads a secret: the only build-time variable is the
// public API base path.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  reactStrictMode: true,
  images: { unoptimized: true },
  // No telemetry, no analytics, no third-party scripts (NFR-3, DPDP).
  poweredByHeader: false,
};

export default nextConfig;
