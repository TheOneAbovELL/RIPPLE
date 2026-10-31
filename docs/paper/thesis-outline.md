# Thesis outline: Ripple — a consistency layer for agent memory
<!-- \documentclass{report} \title{Ripple: A Consistency Layer for Agent Memory} -->
B.Tech final-year project thesis (Omjee R Giri; submission May 2028). Working outline,
chapter by chapter. Every number is a macro (docs/paper/README.md); a refused macro
reads "TBD (pending run)". The written draft is docs/paper/thesis.md (ADR-0136). The
thesis reuses the paper's evidence and adds the
engineering record: requirements, design decisions, the product and the pilot.

Legend: **Supports** (claim, hypothesis or question ids), **Evidence** (macros,
figures), **Sources** (docs, ADRs, learning docs), **Author-owned** (parts the author
writes or implements himself; CLAUDE.md, human-owned work).

## Front matter
<!-- \frontmatter -->
- Certificate, declaration, acknowledgements, abstract (the paper abstract extended
  with the pilot and the engineering contribution), list of figures and tables,
  abbreviations (C, H, Q, I, FR, NFR, ADR ids).

## Chapter: Introduction
<!-- \chapter{Introduction}\label{ch:intro} -->
- Motivation: stale beliefs make long-running agents act wrongly (docs/00 Problem).
- Problem statement and thesis (docs/00 Thesis).
- Objectives = contributions C1–C4; research questions Q1–Q4 (docs/04).
- Scope table: jobs primary, news benchmark, finance unseen domain (docs/00 Scope).
- What the work does not claim (docs/00).
- Organisation of the thesis.
- **Supports** C1–C4, Q1–Q4.

## Chapter: Literature survey
<!-- \chapter{Literature Survey}\label{ch:literature} -->
- Agent memory systems; cascading invalidation (PACMI, rollback repair, MemTX);
  consistency (GEM); temporal graphs (Zep/Graphiti); benchmarks (STALE, RECON);
  belief memory (Nous) — docs/06 table, re-checked before submission.
- Gap: links assumed given, small benchmarks, memory-state metrics only.
- **Supports** positioning of C1, C2. **Sources** docs/06.

## Chapter: Requirements and evaluation plan
<!-- \chapter{Requirements}\label{ch:requirements} -->
- Functional and non-functional requirements (docs/01; FR and NFR ids).
- Invariants I1–I8 as testable requirements, each with its named test.
- Evaluation plan written before results: questions, baselines, ablations, metrics,
  hypotheses and protocol (docs/04), and why evaluation came first (ADR-0012).
- **Supports** the evaluation design behind H1–H4.

## Chapter: System design
<!-- \chapter{System Design}\label{ch:design} -->
- Architecture and module boundaries (docs/02): core, storage, linking, retrieval,
  llm, agents, domains, delivery.
- Data model (docs/03): memories, versions, links, validity states, ChangeEvents.
- Key decisions with their alternatives (ADR index, docs/adr): graph decides scope
  (ADR-0003), Postgres with in-process traversal (ADR-0004), retire never delete
  (ADR-0007), wave-by-wave ripple (ADR-0013), versions as rows (ADR-0014),
  provider-agnostic router (ADR-0010).
- **Sources** docs/02, docs/03, docs/adr.

## Chapter: The ripple engine
<!-- \chapter{The Ripple Engine}\label{ch:engine} -->
- Wave traversal, resolution (rule first, then LLM, ADR-0019), commit protocol,
  asking the user, expiry, forget cascade (I7).
- Correctness argument from the invariants and the scenario suite (tests/scenarios):
  smoke suite {{num:smoke.ripple.scenarios_passed}} of {{num:smoke.ripple.scenarios}}
  scenarios passed (`smoke.ripple.*`).
- **Author-owned**: the WaveEngine body (roadmap Phase 1, [human]).
- **Supports** the mechanism behind C2 and C4. **Sources** docs/learning/ripple-engine.md.

## Chapter: Learning dependency links
<!-- \chapter{Learning Dependency Links}\label{ch:linker} -->
- Pair data (contract C5), provenance, split by persona and template, leakage test,
  hand-check protocol and agreement (WS-14).
- Model and training (ADR-0009). **Author-owned**: the training loop (roadmap Phase 4).
- Results: rule {{num:link.rule.jobs_v0.f1}}, LLM {{num:link.llm.jobs_v0.f1}}, trained
  {{num:link.trained.jobs_v0.f1}} F1 on held-out jobs pairs; transfer to finance
  {{num:link.trained.finance_v1.f1}} (jobs minus finance:
  {{num:h4.transfer_difference_points}} points); hand-check agreement
  {{num:handcheck.jobs_v0.agreement}}.
- Figure `linker_f1`.
- **Supports** C1, H3, H4, Q4.

## Chapter: The job-hunt agent
<!-- \chapter{The Job-Hunt Agent}\label{ch:agent} -->
- Jobs domain adapter: vocabulary, rules, ranking (WS-1); resume and JD parsers (WS-2).
- Agents: conversation, tailor (WS-4), Scout over allowed sources (WS-9, ADR-0008).
- Delivery: API and identity (WS-3), worker and digest (WS-6), Telegram (WS-10), MCP
  server (WS-11), dashboard (WS-12), hardening (WS-13), deployment (WS-8).
- How the agent stays inside I5 (no invented profile facts) and I6 (never applies).
- **Sources** docs/learning/*.md per module.

## Chapter: RippleBench and methodology
<!-- \chapter{RippleBench}\label{ch:bench} -->
- Tracks: jobs v0 ({{num:oracle.v0.check_everything.scenarios}} scenarios,
  {{num:oracle.v0.check_everything.checks}} gold checks), news and finance v1 (WS-15), STALE.
- Generator, split and manifests (ADR-0061); replay harness, time to consistency and
  stale-action window (ADR-0062); metric definitions (ADR-0063).
- Baselines and fairness (ADR-0060); protocol: pinned models, three seeds minimum for
  headline numbers, LLM judge with a human-checked sample (docs/04).
- **Author-owned**: the metric function bodies (roadmap Phase 3).
- **Supports** C2.

## Chapter: Results and discussion
<!-- \chapter{Results}\label{ch:results} -->
- Scripted-oracle sanity replay (no claim): the paper's `tab:sanity` and figure
  `baselines_v0`
  (check-everything passes {{num:oracle.v0.check_everything.pass_share}} of scenarios;
  append-only {{num:oracle.v0.append_only.pass_share}}; newest-wins
  {{num:oracle.v0.newest_wins.pass_share}}; ripple {{num:oracle.v0.ripple.pass_share}}).
- H1: {{num:h1.accuracy_ratio}} of check-everything accuracy at {{num:h1.cost_ratio}}
  of its cost (`tab:h1`, figure `h1_accuracy_cost`).
- H2: stale retrieval rate ripple {{num:mem.ripple.stale_retrieval_rate}} against
  append-only {{num:mem.append_only.stale_retrieval_rate}}.
- Action level (C2): stale recommendation rate ripple
  {{num:mem.ripple.stale_recommendation_rate}}; never-converged share
  {{num:mem.ripple.ttc_share_never_converged}}.
- H3: LLM-minus-trained F1 {{num:h3.f1_difference_points}} points at
  {{num:h3.cost_ratio}} of the cost.
- H4: jobs-minus-finance F1 {{num:h4.transfer_difference_points}} points.
- Ablations: the paper's `tab:ablations` (every `ablation.*` macro).
- Discussion: which hypotheses hold, which do not, and why (docs/00: answered with
  numbers whether they hold or not).
- **Supports** H1–H4, C2, C4.

## Chapter: Pilot study
<!-- \chapter{Pilot Study}\label{ch:pilot} -->
- Recruitment and consent (docs/pilot), onboarding, operations and incidents
  (docs/ops, WS-16), feedback capture.
- Pilot metrics (docs/04): {{num:pilot.students}} students; saved or applied
  {{num:pilot.saved_or_applied_share}}; days earlier than self-discovery
  {{num:pilot.days_earlier_than_self_discovery}}; stale recommendation rate
  {{num:pilot.stale_recommendation_rate}}; question usefulness
  {{num:pilot.question_usefulness_share}}; trust {{num:pilot.trust_score}}.
- Qualitative findings from feedback, quoted with consent.
- **Supports** C3.

## Chapter: Conclusion and future work
<!-- \chapter{Conclusion}\label{ch:conclusion} -->
- Contributions revisited, one paragraph each with its macros.
- Limitations (paper `sec:limits`), future work from docs/IDEAS.md.

## Appendices
<!-- \appendix -->
- ADR index (docs/adr/README.md) and the decisions reversed or amended.
- Invariants and their named tests.
- Reproducibility: results/ layout (results/README.md), `uv run python -m paper.numbers`,
  generated/numbers.json provenance, the I8 check (ADR-0111).
- Consent form and onboarding text (docs/pilot).
- Glossary.
