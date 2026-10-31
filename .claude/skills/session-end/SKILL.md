---
name: session-end
description: Close a work session so the next session knows exactly where things stand
disable-model-invocation: true
---
1. Run fast tests, lint and type check. Report the real results.
2. Append a docs/DEVLOG.md entry using its template.
3. Tick finished roadmap items only if their acceptance check passed.
4. If a module changed meaningfully, update docs/learning/ via /explain.
5. List uncommitted changes and propose a commit message (what + why).
