---
name: plan-phase
description: Turn a roadmap phase into a concrete, reviewable implementation plan
disable-model-invocation: true
argument-hint: <phase number>
---
Plan phase $ARGUMENTS. Do not write code.
1. Read CLAUDE.md, docs/05-roadmap.md (phase $ARGUMENTS), docs/01-requirements.md,
   docs/02-architecture.md, docs/03-data-model.md and all accepted ADRs.
2. Read the existing code relevant to this phase.
3. Write docs/plans/phase-$ARGUMENTS.md with:
   - goal and exit criteria (copied from the roadmap)
   - ordered tasks, each one session long: files touched, tests to write first,
     acceptance check, and whether it is [human]
   - decisions that need new ADRs
   - risks and open questions
4. Ask the architecture-guardian subagent to review the plan; fix what it finds.
5. Present the plan and the open questions. Wait for approval.
