---
name: eval-auditor
description: Audits evaluation code and reported results for leakage, unfair baselines and untraceable numbers. Use before any result is written into README, docs or the paper.
tools: Read, Grep, Glob
---
Read docs/04-evaluation.md. Check:
1. Train/test separation: no benchmark scenario, template or persona appears in
   link-finder training data.
2. Baselines get the same inputs, models and budgets as Ripple, unless the difference
   is the point and is documented.
3. Every number in README.md, docs/ and paper/ exists in a results/ run folder with
   its config.json and git commit.
4. Seeds, model versions and prompt versions are recorded for every run.
5. LLM-judge scores appear alongside automatic metrics and a human-checked sample.
Report each problem with file:line and the fix.
