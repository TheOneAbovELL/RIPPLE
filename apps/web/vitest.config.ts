import path from "node:path";
import { defineConfig } from "vitest/config";

// esbuild's automatic JSX runtime is enough for component tests; no Vite React plugin,
// so the test toolchain adds no dependency beyond vitest, jsdom and Testing Library.
export default defineConfig({
  esbuild: { jsx: "automatic" },
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
    css: false,
    // datetime-local values are read in the browser's zone; pin one so the conversion
    // tests mean the same on every machine (the pilot's zone).
    env: { TZ: "Asia/Kolkata" },
  },
});
