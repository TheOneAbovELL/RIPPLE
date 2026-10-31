import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier/flat";
import jsxA11y from "eslint-plugin-jsx-a11y";

/** @type {import("eslint").Linter.Config[]} */
const config = [
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "coverage/**",
      "src/api/schema.d.ts",
      "next-env.d.ts",
    ],
  },
  ...nextVitals,
  ...nextTs,
  // eslint-config-next already registers the jsx-a11y plugin (recommended rules); adding
  // the plugin again is a config error, so only its stricter rule set is layered on.
  { rules: jsxA11y.flatConfigs.strict.rules },
  prettier,
  {
    rules: {
      // The dashboard shows what the API returns; `any` would hide a shape mismatch.
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/consistent-type-imports": "error",
      "no-console": ["error", { allow: ["warn", "error"] }],
    },
  },
];

export default config;
