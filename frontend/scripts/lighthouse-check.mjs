// Reads the Lighthouse reports in a folder and fails (exit 1) if any page is below the thresholds. Used by CI (see docs/ci.md).
//   node scripts/lighthouse-check.mjs <folder with *.json reports>
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const THRESHOLDS = { performance: 90, accessibility: 95, "best-practices": 90, seo: 90 };
const dir = process.argv[2];
if (!dir) {
  console.error("Usage: node scripts/lighthouse-check.mjs <folder>");
  process.exit(2);
}

const files = readdirSync(dir).filter((f) => f.endsWith(".json")).sort();
if (files.length === 0) {
  console.error(`No Lighthouse reports found in ${dir}`);
  process.exit(2);
}

let failed = false;
for (const f of files) {
  const report = JSON.parse(readFileSync(join(dir, f), "utf8"));
  const scores = Object.fromEntries(Object.entries(report.categories).map(([k, v]) => [k, Math.round(v.score * 100)]));
  const bad = Object.entries(THRESHOLDS).filter(([k, min]) => (scores[k] ?? 0) < min);
  console.log(`${bad.length ? "FAIL" : "ok  "} ${f.padEnd(14)} ${Object.entries(scores).map(([k, v]) => `${k} ${v}`).join(", ")}`);
  for (const [k, min] of bad) console.log(`       ${k} is ${scores[k]}, needs at least ${min}`);
  if (bad.length) failed = true;
}
process.exit(failed ? 1 : 0);
