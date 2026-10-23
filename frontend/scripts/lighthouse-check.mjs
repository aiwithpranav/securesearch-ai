// Reads the Lighthouse reports in a folder and fails (exit 1) if any page is below the thresholds. Used by CI (see docs/ci.md).
//   node scripts/lighthouse-check.mjs <folder with *.json reports>
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

// Performance is lower than on a developer machine because a CI runner is a slow, shared computer: the landing page scores 98 locally
// and 80 on a runner. Accessibility, best practices and SEO do not depend on speed, so they keep high limits.
const THRESHOLDS = { performance: 75, accessibility: 95, "best-practices": 90, seo: 90 };
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

// A page may have several reports (home.1.json, home.2.json, ...): the middle value of each score is used, so one slow moment of a shared runner
// does not fail the build. A single report (login.json) is used as it is.
const median = (values) => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
const groups = new Map();
for (const f of files) {
  const name = f.split(".")[0];
  groups.set(name, [...(groups.get(name) ?? []), f]);
}

let failed = false;
for (const [name, reports] of groups) {
  const all = reports.map((f) => JSON.parse(readFileSync(join(dir, f), "utf8")).categories);
  const scores = Object.fromEntries(
    Object.keys(all[0]).map((k) => [k, median(all.map((c) => Math.round(c[k].score * 100)))]),
  );
  const bad = Object.entries(THRESHOLDS).filter(([k, min]) => (scores[k] ?? 0) < min);
  const runs = reports.length > 1 ? ` (middle of ${reports.length} runs)` : "";
  console.log(`${bad.length ? "FAIL" : "ok  "} ${name.padEnd(10)} ${Object.entries(scores).map(([k, v]) => `${k} ${v}`).join(", ")}${runs}`);
  for (const [k, min] of bad) console.log(`       ${k} is ${scores[k]}, needs at least ${min}`);
  if (bad.length) failed = true;
}
process.exit(failed ? 1 : 0);
