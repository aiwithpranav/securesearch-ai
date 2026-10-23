import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// Lint rules for the frontend: Next.js recommended (React, hooks, accessibility basics, web vitals) plus TypeScript.
export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // Next.js 16 ships React Compiler advisory rules. They flag two long-standing patterns used here (loading data in an
    // effect, creating an animated wrapper component inside a component). Kept as warnings; the count may not grow (see package.json).
    rules: {
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/static-components": "warn",
      "react-hooks/purity": "warn",
    },
  },
  globalIgnores([".next/**", "node_modules/**", "next-env.d.ts", "coverage/**"]),
]);
