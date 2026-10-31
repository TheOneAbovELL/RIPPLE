import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/** .claude/rules/frontend.md: no business logic in the frontend. The rendering tests
 * check that verdicts are printed as the API gave them; this test reads the source and
 * refuses the shapes a client-side rule would take: comparing a fit score, CGPA,
 * eligibility or deadline, or working a memory's state out from its fields. */
const SRC = path.resolve(__dirname, "..", "src");

const FORBIDDEN: { name: string; pattern: RegExp }[] = [
  { name: "comparing a fit score", pattern: /fit_score\s*(?:[<>]=?|===?|!==?)/ },
  { name: "comparing a CGPA or cutoff", pattern: /\b(cgpa|cutoff)\w*\s*(?:[<>]=?|===?|!==?)/i },
  {
    name: "deciding eligibility",
    pattern: /eligible\s*=\s*[^=>]|\beligible\s*[:=]\s*\w+\s*(?:[<>]|&&|\|\|)/,
  },
  {
    name: "comparing a deadline with now",
    pattern: /deadline[^\n]*(Date\.now|new Date\(\))|(Date\.now|new Date\(\))[^\n]*deadline/,
  },
  {
    name: "deriving the flag from the status",
    pattern: /flagged\s*[:=]\s*[^,;\n]*status\s*===?/,
  },
  {
    name: "deriving a status",
    pattern: /status\s*[:=]\s*(?:"VALID"|"SUSPECT"|"PENDING_USER"|"RETIRED")\s*[^,;\n]*\?/,
  },
  {
    name: "ranking or sorting by score",
    pattern: /\.sort\([\s\S]{0,80}?(fit_score|confidence|score)/,
  },
];

function sourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...sourceFiles(full));
    else if (/\.(ts|tsx)$/.test(entry) && !entry.endsWith(".d.ts")) out.push(full);
  }
  return out;
}

describe("no business rule is computed client-side", () => {
  const files = sourceFiles(SRC);

  it("finds the source tree", () => {
    expect(files.length).toBeGreaterThan(10);
  });

  for (const file of files) {
    const relative = path.relative(SRC, file);
    it(`${relative} contains no rule-shaped code`, () => {
      const text = readFileSync(file, "utf8");
      for (const { name, pattern } of FORBIDDEN) {
        expect(pattern.test(text), `${relative}: ${name} (${pattern})`).toBe(false);
      }
    });
  }

  it("the guard itself catches rule-shaped code", () => {
    const samples = [
      "const ok = item.fit_score > 0.5;",
      "const eligible = cgpa >= cutoff;",
      "if (new Date(item.deadline) < new Date()) {}",
      "flagged: memory.status === 'SUSPECT'",
      "list.sort((a, b) => b.fit_score - a.fit_score)",
    ];
    for (const sample of samples) {
      expect(
        FORBIDDEN.some(({ pattern }) => pattern.test(sample)),
        sample,
      ).toBe(true);
    }
  });
});
